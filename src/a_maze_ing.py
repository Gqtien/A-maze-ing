import sys
from typing import Any
from core import Maze, Mode, Pattern, parse_config
from display import Renderer


def main() -> None:
    """Parse config, create maze and renderer, run the renderer."""
    if len(sys.argv) != 2:
        print("Usage: make run <config_file>")
        sys.exit(1)

    try:
        config: dict[str, Any] = parse_config(sys.argv[1])
    except (
        FileNotFoundError,
        ValueError,
        IsADirectoryError,
        PermissionError,
        OSError,
    ) as e:
        print(e)
        sys.exit(1)

    maze: Maze = Maze(
        width=config.get("WIDTH"),
        height=config.get("HEIGHT"),
        entry_pos=config.get("ENTRY"),
        exit_pos=config.get("EXIT"),
        perfect=config.get("PERFECT"),
        seed=config.get("SEED"),
        output_file_name=config.get("OUTPUT_FILE"),
        pattern=config.get("PATTERN", Pattern("42")),
    )

    # print(maze)
    # print(repr(maze))
    # print("seed", maze.seed)

    renderer: Renderer = Renderer(
        config.get("WIN_W", 800),
        config.get("WIN_H", 600),
        config.get("WIN_TITLE", "A-maze-ing !"),
        config.get("FOV", 60),
        config.get("MODE", Mode("wasd")),
        config.get("FPS", False),
        maze,
    )
    renderer.run()


if __name__ == "__main__":
    # NOTE: maybe put main call in a try: catch Exception to avoid all crashes
    main()
