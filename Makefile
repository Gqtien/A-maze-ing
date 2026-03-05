PYTHON		?= python3
VENV_DIR	?= .venv
BIN			:= $(VENV_DIR)/bin
PIP			:= $(BIN)/pip

MAKEFLAGS	:= --no-print-directory

CMDS		:= usage install run compile profile clean lint lint-strict
ARGS		:= $(filter-out $(CMDS),$(MAKECMDGOALS))
DEPS		:= numpy pynput types-pynput
DEPSFLAG	:= $(VENV_DIR)/.installed

export SCREEN_WIDTH := $(shell xrandr --current | grep '*' | uniq | awk '{print $1}' | cut -d 'x' -f1)
export SCREEN_HEIGHT := $(shell xrandr --current | grep '*' | uniq | awk '{print $1}' | cut -d 'x' -f2 | cut -d ' ' -f1)
export REFRESH_RATE := $(shell xrandr --current | awk '/\*/ {print $$2}' | tr -d '*+' | head -n 1)

usage:
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@$(foreach cmd,$(filter-out usage,$(CMDS)), \
		echo "  - $(cmd) $(if $(filter run profile,$(cmd)),<config_file>)";)

install:
	@$(MAKE) clean
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(PIP) install --upgrade pip --quiet
	@$(PIP) install $(DEPS) --quiet
	@$(PIP) install src/assets/mlx-2.2-py3-none-any.whl --quiet
	@$(PIP) install flake8 mypy --quiet
	@touch $(DEPSFLAG)
	@echo "Everything has been installed."
	@echo "You can now run 'make run default_config.txt'"

run:
	@if [ ! -x "$(BIN)/python" -o ! -x "$(BIN)/pip" ]; then \
	    echo "Virtual environment not found. Installing..."; \
	    $(MAKE) install > /dev/null 2>&1; \
	fi
	@if [ ! -f "$(DEPSFLAG)" ]; then \
	    echo "Checking dependencies..."; \
	    missing=$$(for pkg in $(DEPS) mlx; do \
	        $(BIN)/pip list --format=freeze | grep -i "^$${pkg}==" >/dev/null || echo $$pkg; \
	    done); \
	    if [ -n "$$missing" ]; then \
	        echo "Missing dependencies. Installing..."; \
	        $(MAKE) install > /dev/null 2>&1; \
	    fi; \
	fi
	@$(BIN)/$(PYTHON) src/a_maze_ing.py $(ARGS)

compile:
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(PIP) install -U build
	@$(MAZEGEN)
	@$(BIN)/$(PYTHON) -m build
	@rm -f mazegen.py

profile:
	@$(PYTHON) -m venv $(VENV_DIR)
	@$(PIP) install snakeviz --quiet
	@$(BIN)/$(PYTHON) -m cProfile -o profile.prof src/a_maze_ing.py $(ARGS) || true
	@$(BIN)/$(PYTHON) -m snakeviz profile.prof

clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@rm -rf $(VENV_DIR) dist mazegen. egg-info
	@rm -f out.txt profile.prof $(DEPSFLAG)

lint:
	@$(BIN)/$(PYTHON) -m flake8 src || true
	@$(BIN)/$(PYTHON) -m mypy src || true

lint-strict:
	@$(BIN)/$(PYTHON) -m flake8 src || true
	@$(BIN)/$(PYTHON) -m mypy src --strict || true

$(ARGS):
	@:

define MAZEGEN
cat src/assets/digits.py > mazegen.py && printf '\n' >> mazegen.py && printf 'from typing import NamedTuple\n' >> mazegen.py && awk '/^class Pattern/ {flag=1} flag { if ($$0 ~ /^class [A-Za-z_]/ && $$0 !~ /^class Pattern/) exit; print }' src/core/config.py >> mazegen.py && printf '\n' >> mazegen.py && sed -e '/from src\.assets import DIGITS/d' -e '/from src\.core\.config import Pattern/d' src/core/maze.py >> mazegen.py && printf '\n\n__all__ = ["Maze"]\n' >> mazegen.py
endef

.PHONY: $(CMDS) $(ARGS)
