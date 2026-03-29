# Cross The Road

A pixel-style road crossing game made with Python and `pygame`.

## Features

- Fullscreen start menu
- Endless road generation
- Random 1-lane, 2-lane, and later 4-lane roads
- Score system
- Cars that get faster as your score goes up
- Lose screen with restart and close buttons
- Pixel-art player, cars, and sidewalk decorations

## Controls

- `W` = move up
- `A` = move left
- `S` = move down
- `D` = move right
- `ESC` = close the game

## Requirements

- Python 3
- `pygame`

Install `pygame` with:

```bash
pip install pygame
```

## Run The Game

From the project folder, run:

```bash
python CrossTheRoad.py
```

## How Scoring Works

- Each time you fully cross a road and reach the next sidewalk, you earn `100` points.
- As your score increases, the game gets harder.

## Files

- `CrossTheRoad.py` - the game

## Made With

- Python
- Pygame
