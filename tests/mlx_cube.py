import ctypes
import math

import libs.mlx.mlx as mlx

W, H = 800, 600

CUBE = [
    (-1, -1, -1),
    (1, -1, -1),
    (1, 1, -1),
    (-1, 1, -1),
    (-1, -1, 1),
    (1, -1, 1),
    (1, 1, 1),
    (-1, 1, 1),
]

EDGES = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 0),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 4),
    (0, 4),
    (1, 5),
    (2, 6),
    (3, 7),
]

mlx_ctx = mlx.Mlx()
mlx_ptr = mlx_ctx.mlx_init()
win = mlx_ctx.mlx_new_window(mlx_ptr, W, H, "Cube MLX")
img = mlx_ctx.mlx_new_image(mlx_ptr, W, H)

addr, bpp, line_len, endian = mlx_ctx.mlx_get_data_addr(img)
buf = (ctypes.c_uint32 * ((line_len // 4) * H)).from_buffer(addr)

angle = 0.0


def clear():
    for i in range(len(buf)):
        buf[i] = 0x00000000


def put_pixel(x, y, color=0xFFFFFFFF):
    if 0 <= x < W and 0 <= y < H:
        buf[y * (line_len // 4) + x] = color


def project(x, y, z):
    d = 3
    f = 300 / (z + d)
    return int(W / 2 + x * f), int(H / 2 + y * f)


def rotate(p, a):
    x, y, z = p
    ca, sa = math.cos(a), math.sin(a)
    y, z = y * ca - z * sa, y * sa + z * ca
    x, z = x * ca + z * sa, -x * sa + z * ca
    return x, y, z


def draw_line(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        put_pixel(x0, y0)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def loop(_):
    global angle
    clear()

    pts = []
    for p in CUBE:
        rp = rotate(p, angle)
        pts.append(project(*rp))

    for a, b in EDGES:
        draw_line(*pts[a], *pts[b])

    mlx_ctx.mlx_clear_window(mlx_ptr, win)
    mlx_ctx.mlx_put_image_to_window(mlx_ptr, win, img, 0, 0)
    angle += 0.02
    return 0


def key_hook(k, _):
    if k == 65307:
        mlx_ctx.mlx_loop_exit(mlx_ptr)


mlx_ctx.mlx_loop_hook(mlx_ptr, loop, None)
mlx_ctx.mlx_key_hook(win, key_hook, None)
mlx_ctx.mlx_loop(mlx_ptr)
