import sys
from typing import Any, Dict
from src.core import Maze, parse_config
from src.display import render_ascii, run_mlx_2d, run_mlx_3d


def require(config: Dict[str, Any], key: str) -> Any:
    if key not in config:
        print(f"Missing config param : {key!r}")
        exit(1)
    return config[key]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: make run <config_file>")
        exit(1)

    try:
        config: Dict[str, Any] = parse_config(sys.argv[1])
    except (FileNotFoundError, ValueError) as e:
        print(e)
        exit(1)

    maze = Maze(
        width=require(config, "WIDTH"),
        height=require(config, "HEIGHT"),
        entry=require(config, "ENTRY"),
        exit=require(config, "EXIT"),
        perfect=config.get("PERFECT", True),
        seed=config.get("SEED", None),
        output_file_name=config.get("OUTPUT_FILE", None),
    )

    render_ascii(maze)
    # run_mlx_2d(maze)
    run_mlx_3d(maze)
    print(maze.seed)
    return 0


if __name__ == "__main__":
    main()
