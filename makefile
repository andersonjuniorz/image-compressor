# Python interpreter used to create the virtual environment.
# Override it on the command line, e.g. make install PYTHON=python3
PYTHON ?= python3.14

# Virtual environment folder and the Python binary inside it.
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python

# Targets that are commands, not files.
.PHONY: help install run test build-local check clean

# Shows the available commands.
help:
	@echo "Comandos disponíveis:"
	@echo "  make install     - cria o .venv e instala as dependências"
	@echo "  make run         - abre o Image Compressor"
	@echo "  make test        - roda o smoke test do compressor"
	@echo "  make build-local - gera o executável Linux com PyInstaller"
	@echo "  make check       - roda os testes e depois o build (use antes de cada push)"
	@echo "  make clean       - remove arquivos gerados pelo build (mantém o .venv)"

# Creates the virtual environment only if the Python binary is missing.
$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

# Installs the dependencies from requirements.txt into the virtual environment.
install: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements.txt

# Checks that the environment exists, then runs the app with its Python.
run:
	@test -x $(VENV_PYTHON) || (echo "Ambiente não encontrado. Rode 'make install' primeiro." && exit 1)
	$(VENV_PYTHON) main.py

# Runs the smoke test on the compression engine, without opening the GUI.
test: install
	$(VENV_PYTHON) tests/smoke_test.py

# Builds the Linux executable with the same command used by the CI.
build-local: install
	$(VENV_PYTHON) -m pip install pyinstaller
	$(VENV_PYTHON) -m PyInstaller --noconfirm --onefile --windowed --name image-compressor-linux-x86_64 main.py

# Runs the tests, then builds. Use it before every push.
check: test build-local

# Removes the files created by the build and by Python's cache.
# Keeps .venv and your images (ImagesCompressed is not touched).
clean:
	rm -rf build dist
	rm -f image-compressor-linux-x86_64.spec
	find . -path ./$(VENV) -prune -o -type d -name __pycache__ -exec rm -rf {} +
	@echo "Limpeza concluída."
