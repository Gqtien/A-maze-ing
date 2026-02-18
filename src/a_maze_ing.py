import sys
from typing import Any
from core import parse_config
from display import Renderer


if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise ValueError("Usage: make run <config_file>")

        config: dict[str, Any] = parse_config(sys.argv[1])

        renderer: Renderer = Renderer(config)
        renderer.run()
    except Exception as e:
        print(e)
        sys.exit(1)
