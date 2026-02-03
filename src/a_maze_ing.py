import sys
from src.core.mazegen import MazeGenerator
from src.display.ascii_renderer import render_ascii
from src.display.mlx_2d import run_mlx_2d


def main() -> int:
    # TODO: parse config, hardcoded for now
    width = 20
    height = 15
    entry = (0, 0)
    exit = (19, 14)
    perfect = True
    seed = 0

    gen = MazeGenerator(
        width=width,
        height=height,
        entry=entry,
        exit=exit,
        perfect=perfect,
        seed=seed,
    )
    maze = gen.generate()
    render_ascii(maze)
    # run_mlx_2d()
    return 0


if __name__ == "__main__":
    main()
