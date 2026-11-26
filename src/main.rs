use anyhow::{anyhow, bail, Context, Result};
use image::ImageFormat;
use rayon::prelude::*;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;
use walkdir::WalkDir;

const IN_DIR: &str = "ImagesIn";
const OUT_DIR: &str = "ImagesOut";
const FAILED_PREFIX: &str = "FAILED_";

// Compression parameters chosen by the user. They apply to every format.
#[derive(Clone, Copy)]
struct Settings {
    jpeg_quality: u8,
    webp_quality: u8,
    jxl_quality: f32,
    png_level: u8,
    png_lossy: bool,
}

// Defines the supported image formats.
#[derive(Clone, Copy)]
enum Format {
    Png,
    Jpeg,
    Webp,
    Jxl,
}

// Detects the image format based on its file extension.
impl Format {
    fn from_path(path: &Path) -> Option<Format> {
        let ext = path.extension()?.to_str()?.to_ascii_lowercase();
        match ext.as_str() {
            "png" => Some(Format::Png),
            "jpg" | "jpeg" => Some(Format::Jpeg),
            "webp" => Some(Format::Webp),
            "jxl" => Some(Format::Jxl),
            _ => None,
        }
    }
}

// Stores the result of each processed image.
struct Outcome {
    rel: PathBuf,
    original: u64,
    output: u64,
    failed: bool,
}

// Converts any displayable error into an anyhow error.
fn err<E: std::fmt::Display>(e: E) -> anyhow::Error {
    anyhow!("{e}")
}

// Requests a numeric value within the allowed range.
fn ask(label: &str, min: f32, med: f32, max: f32, rec: f32) -> Result<f32> {
    loop {
        print!("{label} (min:{min} med:{med} max:{max}) [recomendado: {rec}]: ");
        io::stdout().flush()?;

        let mut line = String::new();
        io::stdin().read_line(&mut line)?;
        let text = line.trim();

        if text.is_empty() {
            return Ok(rec);
        }

        match text.replace(',', ".").parse::<f32>() {
            Ok(v) if v >= min && v <= max => return Ok(v),
            _ => println!("Valor inválido. Digite um número entre {min} e {max}, ou Enter."),
        }
    }
}

// Requests a yes or no answer with a default option.
fn ask_yes_no(label: &str, default_yes: bool) -> Result<bool> {
    let hint = if default_yes {
        "s/n, recomendado: s"
    } else {
        "s/n, recomendado: n"
    };

    loop {
        print!("{label} ({hint}): ");
        io::stdout().flush()?;

        let mut line = String::new();
        io::stdin().read_line(&mut line)?;

        match line.trim().to_ascii_lowercase().as_str() {
            "" => return Ok(default_yes),
            "s" | "sim" | "y" => return Ok(true),
            "n" | "nao" | "não" => return Ok(false),
            _ => println!("Digite s, n ou Enter."),
        }
    }
}

// Collects all compression settings from the user.
fn ask_settings() -> Result<Settings> {
    println!("Pressione Enter para usar o valor recomendado.\n");

    let jpeg = ask("Qualidade JPEG (0-100)", 60.0, 75.0, 90.0, 85.0)?;
    let webp = ask("Qualidade WebP (0-100)", 60.0, 75.0, 90.0, 85.0)?;
    let jxl = ask("Qualidade JPEG XL (0-100)", 60.0, 75.0, 90.0, 85.0)?;
    let png = ask("Nível de compressão PNG (0-6)", 0.0, 3.0, 6.0, 3.0)?;
    let png_lossy = ask_yes_no("PNG com perda (quantização)?", true)?;
    println!();

    Ok(Settings {
        jpeg_quality: jpeg as u8,
        webp_quality: webp as u8,
        jxl_quality: jxl,
        png_level: png as u8,
        png_lossy,
    })
}

// Decodes a JPEG XL image and converts its pixels to RGBA.
fn decode_jxl(bytes: &[u8]) -> Result<(u32, u32, Vec<u8>)> {
    let image = jxl_oxide::JxlImage::builder().read(bytes).map_err(err)?;
    let render = image.render_frame(0).map_err(err)?;
    let frame = render.image_all_channels();

    let w = frame.width() as u32;
    let h = frame.height() as u32;
    let channels = frame.channels();
    let to8 = |v: f32| (v.clamp(0.0, 1.0) * 255.0).round() as u8;

    let mut rgba = Vec::with_capacity((w * h * 4) as usize);
    for px in frame.buf().chunks_exact(channels) {
        match channels {
            1 => {
                let g = to8(px[0]);
                rgba.extend_from_slice(&[g, g, g, 255]);
            }
            2 => {
                let g = to8(px[0]);
                rgba.extend_from_slice(&[g, g, g, to8(px[1])]);
            }
            3 => rgba.extend_from_slice(&[to8(px[0]), to8(px[1]), to8(px[2]), 255]),
            4 => rgba.extend_from_slice(&[to8(px[0]), to8(px[1]), to8(px[2]), to8(px[3])]),
            _ => bail!("JPEG XL com {channels} canais não é suportado"),
        }
    }

    Ok((w, h, rgba))
}

// Encodes RGBA pixel data into JPEG XL format.
fn encode_jxl(rgba: &[u8], w: u32, h: u32, quality: f32) -> Result<Vec<u8>> {
    let mut encoder = jpegxl_rs::encoder_builder()
        .quality(quality)
        .build()
        .map_err(err)?;

    let result = encoder.encode::<u8, u8>(rgba, w, h).map_err(err)?;
    Ok(result.data)
}

/// Quantiza o PNG para até 256 cores e grava como PNG indexado.
fn png_quantize(bytes: &[u8], level: u8) -> Result<Vec<u8>> {
    let img = image::load_from_memory_with_format(bytes, ImageFormat::Png)?.to_rgba8();
    let (w, h) = img.dimensions();

    // Converts the pixel data into the format required by imagequant.
    let pixels: Vec<imagequant::RGBA> = img
        .as_raw()
        .chunks_exact(4)
        .map(|p| imagequant::RGBA::new(p[0], p[1], p[2], p[3]))
        .collect();

    // Creates the quantizer and defines the allowed quality range.
    let mut attr = imagequant::new();
    attr.set_quality(60, 90).map_err(err)?;

    // Reduces the image palette and generates indexed pixel data.
    let mut image = attr
        .new_image(pixels, w as usize, h as usize, 0.0)
        .map_err(err)?;
    let mut result = attr.quantize(&mut image).map_err(err)?;
    let (palette, indexed) = result.remapped(&mut image).map_err(err)?;

    // Writes the indexed PNG using the generated palette.
    let mut out = Vec::new();
    {
        let mut encoder = png::Encoder::new(&mut out, w, h);
        encoder.set_color(png::ColorType::Indexed);
        encoder.set_depth(png::BitDepth::Eight);

        let rgb: Vec<u8> = palette.iter().flat_map(|c| [c.r, c.g, c.b]).collect();
        let alpha: Vec<u8> = palette.iter().map(|c| c.a).collect();
        encoder.set_palette(rgb);
        encoder.set_trns(alpha);

        let mut writer = encoder.write_header()?;
        writer.write_image_data(&indexed)?;
    }

    // Optimizes the generated PNG and removes safe metadata.
    let mut opts = oxipng::Options::from_preset(level);
    opts.strip = oxipng::StripChunks::Safe;
    oxipng::optimize_from_memory(&out, &opts).map_err(err)
}

// Compresses the image bytes using the method for its format.
fn compress(format: Format, bytes: &[u8], s: Settings) -> Result<Vec<u8>> {
    match format {
        Format::Png => {
            let mut opts = oxipng::Options::from_preset(s.png_level);
            opts.strip = oxipng::StripChunks::Safe;
            let lossless = oxipng::optimize_from_memory(bytes, &opts).map_err(err)?;

            if !s.png_lossy {
                return Ok(lossless);
            }

            // Quantizes the PNG to at most 256 colors and writes it as an indexed PNG.
            match png_quantize(bytes, s.png_level) {
                Ok(q) if q.len() < lossless.len() => Ok(q),
                _ => Ok(lossless),
            }
        }

        Format::Jpeg => {
            let img = image::load_from_memory_with_format(bytes, ImageFormat::Jpeg)?.to_rgb8();
            let (w, h) = img.dimensions();

            let mut out = Vec::new();
            jpeg_encoder::Encoder::new(&mut out, s.jpeg_quality)
                .encode(
                    img.as_raw(),
                    w as u16,
                    h as u16,
                    jpeg_encoder::ColorType::Rgb,
                )
                .map_err(err)?;
            Ok(out)
        }

        Format::Webp => {
            let dynimg = image::load_from_memory_with_format(bytes, ImageFormat::WebP)?;
            let (w, h) = (dynimg.width(), dynimg.height());
            let q = s.webp_quality as f32;

            let mem = if dynimg.color().has_alpha() {
                let rgba = dynimg.to_rgba8();
                webp::Encoder::from_rgba(rgba.as_raw(), w, h).encode(q)
            } else {
                let rgb = dynimg.to_rgb8();
                webp::Encoder::from_rgb(rgb.as_raw(), w, h).encode(q)
            };
            Ok(mem.to_vec())
        }

        Format::Jxl => {
            let (w, h, rgba) = decode_jxl(bytes)?;
            encode_jxl(&rgba, w, h, s.jxl_quality)
        }
    }
}

// Builds the FAILED_ path for an output file.
fn failed_path_of(path: &Path) -> PathBuf {
    let name = path.file_name().unwrap_or_default().to_string_lossy();
    path.with_file_name(format!("{FAILED_PREFIX}{name}"))
}

// Processes one image and saves its compressed result.
fn process(input: &Path, rel: &Path, out_root: &Path, s: Settings) -> Result<Outcome> {
    let format = Format::from_path(input).context("formato não suportado")?;
    let original_bytes = fs::read(input)?;
    let original = original_bytes.len() as u64;

    // Compresses the image in memory before touching the output folder.
    let compressed = compress(format, &original_bytes, s)
        .with_context(|| format!("falha ao comprimir {}", rel.display()))?;

    let out_path = out_root.join(rel);
    let failed_path = failed_path_of(&out_path);

    if let Some(parent) = out_path.parent() {
        fs::create_dir_all(parent)?;
    }

    // Removes any FAILED_ file left by a previous execution.
    let _ = fs::remove_file(&failed_path);

    // Saves the compressed image and checks whether its size increased.
    fs::write(&out_path, &compressed)?;
    let output = compressed.len() as u64;
    let failed = output > original;

    // Moves larger files to a separate FAILED_ filename.
    if failed {
        fs::rename(&out_path, &failed_path)?;
    }

    Ok(Outcome {
        rel: rel.to_path_buf(),
        original,
        output,
        failed,
    })
}

// Converts file sizes into a readable format.
fn fmt_size(bytes: u64) -> String {
    if bytes >= 1024 * 1024 {
        format!("{:.2} MB", bytes as f64 / (1024.0 * 1024.0))
    } else {
        format!("{:.1} KB", bytes as f64 / 1024.0)
    }
}

// Calculates the percentage of space saved or increased.
fn saving(original: u64, output: u64) -> f64 {
    if original == 0 {
        0.0
    } else {
        (1.0 - output as f64 / original as f64) * 100.0
    }
}

// Creates the input folder and exits so the user can add images.
fn main() -> Result<()> {
    println!("====================================");
    println!("            IMAGE-COMPRESS");
    println!("====================================\n");

    // Defines the input and output directories.
    let in_root = PathBuf::from(IN_DIR);
    let out_root = PathBuf::from(OUT_DIR);

    // Creates the input directory if it does not exist.
    if !in_root.is_dir() {
        fs::create_dir_all(&in_root)?;
        println!("A pasta {IN_DIR} foi criada. Coloque as imagens nela e rode novamente.");
        return Ok(());
    }
    fs::create_dir_all(&out_root)?;

    // Collects the compression settings.
    let settings = ask_settings()?;

    // Finds all supported images inside the input directory.
    let files: Vec<PathBuf> = WalkDir::new(&in_root)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .map(|e| e.into_path())
        .filter(|p| Format::from_path(p).is_some())
        .collect();

    if files.is_empty() {
        println!("Nenhuma imagem PNG, JPG, WebP ou JXL encontrada em {IN_DIR}.");
        return Ok(());
    }

    println!("Arquivos encontrados: {}\n", files.len());
    let start = Instant::now();

    // Processes all images in parallel using Rayon.
    let results: Vec<Result<Outcome>> = files
        .par_iter()
        .map(|file| {
            let rel = file
                .strip_prefix(&in_root)
                .context("caminho inválido")?
                .to_path_buf();
            process(file, &rel, &out_root, settings)
        })
        .collect();

    // Totals include only successful files. FAILED_ files are counted separately.
    let mut total_original = 0u64;
    let mut total_output = 0u64;
    let mut ok = 0usize;
    let mut failed = 0usize;
    let mut errors = 0usize;

    // Displays the result of each processed image.
    for result in results {
        match result {
            Ok(o) => {
                let s = saving(o.original, o.output);
                if o.failed {
                    failed += 1;
                    println!(
                        "[FAILED_] {} | {} -> {} | aumentou {:.2}%",
                        o.rel.display(),
                        fmt_size(o.original),
                        fmt_size(o.output),
                        -s
                    );
                } else {
                    ok += 1;
                    total_original += o.original;
                    total_output += o.output;
                    println!(
                        "[OK] {} | {} -> {} | economia {:.2}%",
                        o.rel.display(),
                        fmt_size(o.original),
                        fmt_size(o.output),
                        s
                    );
                }
            }
            Err(e) => {
                errors += 1;
                eprintln!("[ERRO] {e:#}");
            }
        }
    }

    // Displays the final compression statistics and execution time.
    println!("\n====================================");
    println!("             RESULTADO");
    println!("====================================");
    println!("Comprimidos: {ok}");
    println!("FAILED_ (maiores que o original): {failed}");
    println!("Erros: {errors}");
    println!("Original (OK): {}", fmt_size(total_original));
    println!("Final (OK): {}", fmt_size(total_output));
    println!(
        "Economia (OK): {:.2}%",
        saving(total_original, total_output)
    );
    println!("Tempo: {:.2}s", start.elapsed().as_secs_f64());
    println!("====================================");

    Ok(())
}
