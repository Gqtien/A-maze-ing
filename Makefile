PYTHON		?= python3
VENV_DIR	?= .venv
BIN			:= $(VENV_DIR)/bin
PIP			:= $(BIN)/pip

install:
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install flake8 mypy

run:
	$(PYTHON) -m src.a_maze_ing

debug:
	$(PYTHON) -m src.a_maze_ing

clean:
	rm -rf **/*__pycache__ **/*.mypy_cache **/*.pytest_cache

lint:
	flake8 .
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs

lint-strict:
	flake8 .
	$(PYTHON) -m mypy . --strict

.PHONY: install run debug clean lint lint-strict
