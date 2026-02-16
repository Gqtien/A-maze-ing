import sys
from typing import Any
from core import Maze, parse_config
from display import Renderer


def require(config: dict[str, Any], key: str) -> Any:
    # NOTE: same as dict[key], that would raise an error ?
    if key not in config:
        print(f"Missing config param : {key!r}")
        exit(1)
    return config[key]


def main() -> None:
    """Parse config, create maze and renderer, run the renderer."""
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
        seed=config.get("SEED"),
        output_file_name=config.get("OUTPUT_FILE"),
    )

    print(maze)
    print(repr(maze))
    print("seed", maze.seed)

    renderer = Renderer(
        config.get("WIN_W", 800),
        config.get("WIN_H", 600),
        config.get("WIN_TITLE", "A-maze-ing !"),
        config.get("FOV", 60),
        maze,
    )
    renderer.run()


if __name__ == "__main__":
    main()
