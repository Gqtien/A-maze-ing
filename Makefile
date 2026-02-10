PYTHON		?= python3
VENV_DIR	?= .venv
BIN			:= $(VENV_DIR)/bin
PIP			:= $(BIN)/pip

CMDS := usage install run debug clean lint lint-strict profile
ARGS := $(filter-out $(CMDS),$(MAKECMDGOALS))

export SCREEN_WIDTH := $(shell xrandr --current | grep '*' | uniq | awk '{print $1}' | cut -d 'x' -f1)
export SCREEN_HEIGHT := $(shell xrandr --current | grep '*' | uniq | awk '{print $1}' | cut -d 'x' -f2 | cut -d ' ' -f1)

usage:
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@$(foreach cmd,$(filter-out usage,$(CMDS)), \
		echo "  - $(cmd) $(if $(filter run debug,$(cmd)),<config_file>)";)

install:
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install flake8 mypy

run:
	@$(PYTHON) -m src.a_maze_ing $(ARGS) || true

profile:
	@$(PYTHON) -m cProfile -m src.a_maze_ing $(ARGS) || true

debug:
	@$(PYTHON) -m src.a_maze_ing --debug $(ARGS) || true

clean:
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +


lint:
	flake8 src || true
	mypy src --exclude 'libs' --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs || true

lint-strict:
	flake8 src || true
	mypy src --strict || true

$(ARGS):
	@:

.PHONY: $(CMDS) $(ARGS)
