PYTHON		?= python3
VENV_DIR	?= .venv
BIN			:= $(VENV_DIR)/bin
PIP			:= $(BIN)/pip

CMDS := usage install run compile profile clean lint lint-strict
ARGS := $(filter-out $(CMDS),$(MAKECMDGOALS))

export SCREEN_WIDTH := $(shell xrandr --current | grep '*' | uniq | awk '{print $1}' | cut -d 'x' -f1)
export SCREEN_HEIGHT := $(shell xrandr --current | grep '*' | uniq | awk '{print $1}' | cut -d 'x' -f2 | cut -d ' ' -f1)
export REFRESH_RATE := $(shell xrandr --current | awk '/\*/ {print $$2}' | tr -d '*+')

usage:
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@$(foreach cmd,$(filter-out usage,$(CMDS)), \
		echo "  - $(cmd) $(if $(filter run profile,$(cmd)),<config_file>)";)

install:
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@$(PIP) install src/assets/mlx-2.2-py3-none-any.whl
	@$(PIP) install flake8 mypy
	@echo "Environment created."
	@echo "Run: source $(VENV_DIR)/bin/activate"
	@echo "Then: make run default_config.txt"

run:
	@$(PYTHON) src/a_maze_ing.py $(ARGS) || true

compile:
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(PIP) install -U build
	@$(MAZEGEN)
	@$(BIN)/$(PYTHON) -m build
	@rm -f mazegen.py

profile:
	@$(PYTHON) -m cProfile src/a_maze_ing.py $(ARGS) || true

clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@rm -rf $(VENV_DIR)
	@rm -rf dist
	@rm -rf mazegen.egg-info
	@rm -f out.txt

lint:
	@flake8 src || true
	@mypy src --exclude 'libs' --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs || true

lint-strict:
	@flake8 src || true
	@mypy src --strict || true

$(ARGS):
	@:

define MAZEGEN
cat src/assets/digits.py > mazegen.py && printf '\n' >> mazegen.py && printf 'from typing import NamedTuple\n' >> mazegen.py && awk '/^class Pattern/ {flag=1} flag { if ($$0 ~ /^class [A-Za-z_]/ && $$0 !~ /^class Pattern/) exit; print }' src/core/config.py >> mazegen.py && printf '\n' >> mazegen.py && sed -e '/from src\.assets import DIGITS/d' -e '/from src\.core\.config import Pattern/d' src/core/maze.py >> mazegen.py && printf '\n\n__all__ = ["Maze"]\n' >> mazegen.py
endef

.PHONY: $(CMDS) $(ARGS)
