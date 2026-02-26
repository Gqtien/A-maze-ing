*This project has been created as part of the 42 curriculum by gviola-l, mphippen.*

# A-Maze-Ing x MiniCub3D

<a name="header"></a>
[![language](https://img.shields.io/badge/language-Python-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![platform](https://img.shields.io/badge/platform-Linux-FCC624?logo=linux&logoColor=white)](https://www.x.org/wiki/)
[![rendering](https://img.shields.io/badge/rendering-Raycasting-FF6F00)]()
[![style](https://img.shields.io/badge/style-Wolfenstein--like-8B0000)]()
[![algo](https://img.shields.io/badge/algorithm-DDA-blueviolet)]()

## Table of Contents
- [Description](#description)
- [How To Run](#run)
- [Configuration](#config)
- [Reusability](#reusability)
- [Resources](#resources)
- [Contributions](#contributions)

---

<a name=run></a>
## 📝 | How to Run

To run the project, follow these steps:

```shell
# Ensure Git and Python 3.10 are installed

# Clone the repository
git clone https://github.com/Gqtien/A-maze-ing.git
cd A-Maze-Ing

# Install dependencies
make install

# Run the program in the virtual environment
source .venv/bin/activate
make run default_config.txt
```

 ---

<a name=config></a>
## `⚙️` | Configuration
### Maze Settings

| Key       | Description                         | Valid Values / Notes                  |
| --------- | ----------------------------------- | ------------------------------------- |
| `WIDTH`   | Width of the maze                   | Integer > 0 and < 1000                |
| `HEIGHT`  | Height of the maze                  | Integer > 0 and < 1000                |
| `ENTRY`   | Coordinates of the maze entry point | Must be within maze boundaries        |
| `EXIT`    | Coordinates of the maze exit point  | Must be within maze boundaries        |
| `PERFECT` | Whether the maze is perfect         | Perfect = exactly one unique solution |
| `ALGO`    | Maze generation algorithm           | `backtracking`, `prim`                |
| `PATTERN` | Digits used for center pattern      | Exactly 2 valid digits                |

---

### Window Settings

| Key         | Description               | Valid Values / Notes   |
| ----------- | ------------------------- | ---------------------- |
| `WIN_W`     | Width of the game window  | >0 and < screen width  |
| `WIN_H`     | Height of the game window | >0 and < screen height |
| `WIN_TITLE` | Title of the game window  | Any string             |
| `FOV`       | Field of view (degrees)   | >20 and < 120          |
| `FPS`       | FPS indicator             | True / False           |

---

### Gameplay Settings

| Key              | Description               | Valid Values / Notes                |
| ---------------- | ------------------------- | ----------------------------------- |
| `MODE`           | Movement key bindings     | Exactly 4 valid keyboard characters |
| `MOUSE`          | Mouse controls            | True / False                        |
| `PLAYBACK_SPEED` | Playback speed multiplier | > 0                                 |
| `SOLUTION`       | Show solution at startup  | True / False                        |

---

### Visual Settings

| Key     | Description | Valid Values / Notes                                         |
| ------- | ----------- | ------------------------------------------------------------ |
| `COLOR` | Wall color  | `Cyan`, `White`, `Blue`, `Magenta`, `Red`, `Green`, `Yellow` |

---

### Output Settings

| Key           | Description            | Valid Values / Notes |
| ------------- | ---------------------- | -------------------- |
| `OUTPUT_FILE` | Path to save maze data | Any valid file path  |
