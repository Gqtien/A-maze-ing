import sys
from typing import Any
from core import Maze, parse_config
from display import run_mlx_3d


def require(config: dict[str, Any], key: str) -> Any:
    # NOTE: same as dict[key], that would raise an error ?
    if key not in config:
        print(f"Missing config param : {key!r}")
        exit(1)
    return config[key]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: make run <config_file>")
        exit(1)

    try:
        config: dict[str, Any] = parse_config(sys.argv[1])
    except (FileNotFoundError, ValueError, IsADirectoryError) as e:
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

    print(maze)
    print(repr(maze))

    settings = {
        "ENTRY": require(config, "ENTRY"),
        "EXIT": require(config, "EXIT"),
        "WIN_W": config.get("WIN_W", 800),
        "WIN_H": config.get("WIN_H", 600),
        "WIN_TITLE": config.get("WIN_TITLE", "A-Maze-Ing"),
        "FOV": config.get("FOV", 60)
    }
    run_mlx_3d(maze, settings)

    print("seed", maze.seed)
    return 0


if __name__ == "__main__":
    main()
