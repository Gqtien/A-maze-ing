import sys
import libs.mlx.mlx as mlx


def run_mlx_2d() -> None:
    mlx_ctx = mlx.Mlx()
    mlx_ptr = mlx_ctx.mlx_init()
    win_ptr = mlx_ctx.mlx_new_window(mlx_ptr, 1920, 1080, "A-Maze-Ing")
    image = mlx_ctx.mlx_new_image(mlx_ptr, 1920, 1080)

    def loop(param: int) -> None:
        for x in range(100):
            for y in range(100):
                mlx_ctx.mlx_pixel_put(mlx_ptr, win_ptr, 500 + x, y, 0xFFFF0000)
        mlx_ctx.mlx_put_image_to_window(mlx_ptr, win_ptr, image, 0, 0)

    def key_hook(key: int, param: int) -> None:
        match key:
            case 65307:
                mlx_ctx.mlx_loop_exit(mlx_ptr)
            case _:
                print(f"Pressed key: {key}")

    mlx_ctx.mlx_loop_hook(mlx_ptr, loop, param=mlx_ptr)
    mlx_ctx.mlx_key_hook(win_ptr, key_hook, param=mlx_ptr)
    mlx_ctx.mlx_loop(mlx_ptr)
