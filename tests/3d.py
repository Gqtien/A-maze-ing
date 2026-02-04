import ctypes
import math
import libs.mlx.mlx as mlx

# --- CONFIGURATION ---
RENDER_SCALE = 0.5
WIN_W, WIN_H = int(1280 * RENDER_SCALE), int(720 * RENDER_SCALE)
HALF_H = WIN_H // 2
VELOCITY = 0.050
VELOCITY_SPRINT = VELOCITY * 1.8
VELOCITY_ROT = 0.05
FOV_DEFAULT = 90

# Key Codes
KEY_W = 119
KEY_A = 97
KEY_S = 115
KEY_D = 100
KEY_ESC = 65307
KEY_LEFT = 65361
KEY_RIGHT = 65363
KEY_SHIFT = 65505

DEFAULT_MAP = """
111111111111111111
1S0010000000100001
111010111110101101
100000100010001001
101111101011101011
100000101000001001
111110011111111011
100010100000000001
101010101111111101
101000000000000001
101111111111111001
111111111111111111
""".strip().split('\n')

class Image:
    def __init__(self, mlx_ctx, mlx_ptr, w, h):
        self.w, self.h = w, h
        self.ptr = mlx_ctx.mlx_new_image(mlx_ptr, w, h)
        addr, bpp, line_len, endian = mlx_ctx.mlx_get_data_addr(self.ptr)
        
        self.w_size = line_len // 4
        self.size = self.w_size * h
        
        # --- FIX 1: Passage par raw_bytes ---
        # On récupère d'abord le pointeur sous forme d'octets (unsigned byte)
        self.raw_bytes = (ctypes.c_ubyte * (line_len * h)).from_buffer(addr)
        self.raw_addr = ctypes.addressof(self.raw_bytes)
        
        # On cast les octets ('B') vers des entiers non signés ('I')
        # C'est la méthode robuste qui marche sur toutes les versions de Python 3
        self.buf = memoryview(self.raw_bytes).cast('I')

class Texture:
    def __init__(self, color1, color2, size=64):
        self.w = self.h = self.w_size = size
        raw_array = (ctypes.c_uint32 * (size * size))()
        
        # Création du pattern
        for i in range(size * size):
            y, x = divmod(i, size)
            raw_array[i] = color1 if (((x // 8) ^ (y // 8)) & 1) == 0 else color2
            
        # --- FIX 2: Double Cast ---
        # On prend le tableau ctypes -> vue en bytes -> vue en Int natif
        self.buf = memoryview(raw_array).cast('B').cast('I')

class Map:
    def __init__(self, game_map, player_x, player_y, player_angle, floor_color, ceiling_color):
        self.mlx_ctx = mlx.Mlx()
        self.mlx_ptr = self.mlx_ctx.mlx_init()
        self.win = self.mlx_ctx.mlx_new_window(self.mlx_ptr, WIN_W, WIN_H, "A-Maze-Ing Optimized")
        self.frame = Image(self.mlx_ctx, self.mlx_ptr, WIN_W, WIN_H)
        
        self.ceiling_color = ceiling_color
        self.floor_color = floor_color
        self._build_clear_buffers()
        
        self.map_h = len(game_map)
        self.map_w = len(game_map[0])
        self.flat_map = [1 if c == '1' else 0 for row in game_map for c in row]
        
        self.pos_x, self.pos_y, self.angle = player_x, player_y, player_angle
        
        self.fov_rad = FOV_DEFAULT * (math.pi / 180)
        self.plane_len = math.tan(self.fov_rad / 2)
        
        self.keys = set()
        
        self.tex_n = Texture(0xFF800000, 0xFF600000)
        self.tex_s = Texture(0xFF008000, 0xFF006000)
        self.tex_e = Texture(0xFF000080, 0xFF000060)
        self.tex_w = Texture(0xFF808000, 0xFF606000)

    def _build_clear_buffers(self):
        half_pixels = WIN_W * HALF_H
        self.ceil_buf = (ctypes.c_uint32 * half_pixels)(*[self.ceiling_color] * half_pixels)
        self.floor_buf = (ctypes.c_uint32 * half_pixels)(*[self.floor_color] * half_pixels)
        self.ceil_size = half_pixels * 4
        self.floor_size = half_pixels * 4

    def clear_frame(self):
        ctypes.memmove(self.frame.raw_addr, ctypes.addressof(self.ceil_buf), self.ceil_size)
        offset = self.ceil_size
        if WIN_H % 2 != 0: 
             offset += WIN_W * 4
        ctypes.memmove(self.frame.raw_addr + offset, ctypes.addressof(self.floor_buf), self.floor_size)

    def is_collision(self, x, y):
        ix, iy = int(x), int(y)
        if 0 <= ix < self.map_w and 0 <= iy < self.map_h:
            return self.flat_map[iy * self.map_w + ix] == 1
        return True

    def raycasts(self):
        pos_x, pos_y = self.pos_x, self.pos_y
        dir_x, dir_y = math.cos(self.angle), math.sin(self.angle)
        plane_x, plane_y = -dir_y * self.plane_len, dir_x * self.plane_len
        
        w, h = WIN_W, WIN_H
        map_w, map_h = self.map_w, self.map_h
        flat_map = self.flat_map
        buf = self.frame.buf
        w_size = self.frame.w_size
        
        tex_n, tex_s = self.tex_n, self.tex_s
        tex_e, tex_w = self.tex_e, self.tex_w
        tex_size = 64
        tex_mask = tex_size - 1
        
        # Rendu 1 colonne sur 2 pour performance (pixel art style)
        step_render = 2
        
        for x in range(0, w, step_render):
            camera_x = 2 * x / w - 1
            ray_dir_x = dir_x + plane_x * camera_x
            ray_dir_y = dir_y + plane_y * camera_x
            
            map_x, map_y = int(pos_x), int(pos_y)
            
            delta_dist_x = abs(1 / ray_dir_x) if ray_dir_x != 0 else 1e30
            delta_dist_y = abs(1 / ray_dir_y) if ray_dir_y != 0 else 1e30
            
            step_x = 1 if ray_dir_x >= 0 else -1
            side_dist_x = (map_x + 1.0 - pos_x) * delta_dist_x if ray_dir_x >= 0 else (pos_x - map_x) * delta_dist_x

            step_y = 1 if ray_dir_y >= 0 else -1
            side_dist_y = (map_y + 1.0 - pos_y) * delta_dist_y if ray_dir_y >= 0 else (pos_y - map_y) * delta_dist_y
            
            hit = 0
            side = 0
            
            for _ in range(50):
                if side_dist_x < side_dist_y:
                    side_dist_x += delta_dist_x
                    map_x += step_x
                    side = 0
                else:
                    side_dist_y += delta_dist_y
                    map_y += step_y
                    side = 1
                
                if map_x < 0 or map_x >= map_w or map_y < 0 or map_y >= map_h:
                    hit = 2
                    break
                    
                if flat_map[map_y * map_w + map_x] == 1:
                    hit = 1
                    break
            
            if hit == 2: continue

            if side == 0:
                perp_wall_dist = (side_dist_x - delta_dist_x)
            else:
                perp_wall_dist = (side_dist_y - delta_dist_y)

            if perp_wall_dist < 0.05: perp_wall_dist = 0.05
            
            line_height = int(h / perp_wall_dist)
            
            draw_start = -line_height // 2 + h // 2
            if draw_start < 0: draw_start = 0
            draw_end = line_height // 2 + h // 2
            if draw_end >= h: draw_end = h - 1

            if side == 0:
                wall_x = pos_y + perp_wall_dist * ray_dir_y
                tex = tex_w if ray_dir_x > 0 else tex_e
            else:
                wall_x = pos_x + perp_wall_dist * ray_dir_x
                tex = tex_s if ray_dir_y > 0 else tex_n
                
            wall_x -= int(wall_x)
            tex_x = int(wall_x * tex_size)
            if (side == 0 and ray_dir_x > 0) or (side == 1 and ray_dir_y < 0):
                tex_x = tex_size - tex_x - 1
            
            step = 1.0 * tex_size / line_height
            tex_pos = (draw_start - h / 2 + line_height / 2) * step
            
            tex_buf = tex.buf
            
            ptr_base = draw_start * w_size + x
            draw_double_x = (x + 1 < w)
            
            # Boucle Y optimisée (saut de 2 pixels)
            for y in range(draw_start, draw_end, 2):
                tex_y = int(tex_pos) & tex_mask
                tex_pos += step * 2
                
                color = tex_buf[tex_y * tex_size + tex_x]
                
                buf[ptr_base] = color
                if draw_double_x: buf[ptr_base + 1] = color
                
                if y + 1 < draw_end:
                    buf[ptr_base + w_size] = color
                    if draw_double_x: buf[ptr_base + w_size + 1] = color
                
                ptr_base += w_size * 2

    def move(self):
        if KEY_LEFT in self.keys: self.angle -= VELOCITY_ROT
        if KEY_RIGHT in self.keys: self.angle += VELOCITY_ROT
        
        move_step = 0
        if KEY_W in self.keys: move_step = 1
        elif KEY_S in self.keys: move_step = -1
        
        strafe_step = 0
        if KEY_D in self.keys: strafe_step = 1
        elif KEY_A in self.keys: strafe_step = -1
        
        if move_step == 0 and strafe_step == 0: return

        speed = VELOCITY_SPRINT if KEY_SHIFT in self.keys else VELOCITY
        
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        
        dx = (cos_a * move_step - sin_a * strafe_step) * speed
        dy = (sin_a * move_step + cos_a * strafe_step) * speed

        if not self.is_collision(self.pos_x + dx * 2, self.pos_y):
            self.pos_x += dx
        if not self.is_collision(self.pos_x, self.pos_y + dy * 2):
            self.pos_y += dy

    def loop(self, _):
        self.move()
        self.clear_frame()
        self.raycasts()
        self.mlx_ctx.mlx_put_image_to_window(self.mlx_ptr, self.win, self.frame.ptr, 0, 0)
        return 0

    def key_press(self, key, _):
        if key == KEY_ESC: self.mlx_ctx.mlx_loop_exit(self.mlx_ptr)
        self.keys.add(key)
        return 0

    def key_release(self, key, _):
        self.keys.discard(key)
        return 0

    def run(self):
        self.mlx_ctx.mlx_loop_hook(self.mlx_ptr, self.loop, None)
        self.mlx_ctx.mlx_hook(self.win, 2, 1, self.key_press, None)
        self.mlx_ctx.mlx_hook(self.win, 3, 2, self.key_release, None)
        self.mlx_ctx.mlx_hook(self.win, 9, 0, lambda _: self.keys.clear(), None) 
        self.mlx_ctx.mlx_loop(self.mlx_ptr)

def main():
    game_map = list(DEFAULT_MAP)
    player_x, player_y, player_angle = 1.5, 1.5, 0
    
    for y, row in enumerate(game_map):
        if 'S' in row:
            x = row.index('S')
            player_x, player_y = x + 0.5, y + 0.5
            game_map[y] = row.replace('S', '0')
            player_angle = math.pi
            break
            
    Map(game_map, player_x, player_y, player_angle, 0xFF303030, 0xFF101010).run()

if __name__ == "__main__":
    main()