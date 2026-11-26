.PHONY: help run

help:
	@echo "Comandos disponíveis:"
	@echo "  make help  - mostra esta ajuda"
	@echo "  make run   - executa ./target/release/image-compress"

run:
	./target/release/image-compress
