import sys
from typing import Any, Mapping
from src.core import MazeGenerator, parse_config
from src.display import render_ascii, run_mlx_2d


def require(cfg: Mapping[str, Any], key: str) -> Any:
    if key not in cfg:
        raise ValueError(f"Missing {key}")
    return cfg[key]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: make run <config_file>")
        return 1

    try:
        config = parse_config(sys.argv[1])
    except (FileNotFoundError, ValueError) as e:
        print(e)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    gen = MazeGenerator(
        width=require(config, "WIDTH"),
        height=require(config, "HEIGHT"),
        entry=require(config, "ENTRY"),
        exit=require(config, "EXIT"),
        perfect=config.get("PERFECT", True),
        seed=config.get("SEED", 0),
        output_file_name=config.get("OUTPUT_FILE", None),
    )
    maze = gen.generate()
    render_ascii(maze)
    # run_mlx_2d()
    return 0


if __name__ == "__main__":
    main()
