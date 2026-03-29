import random
import sys
from pathlib import Path

import pygame


BACKGROUND_COLOR = (122, 122, 122)
ROAD_COLOR = (56, 56, 56)
STRIPE_COLOR = (245, 245, 245)
MENU_BLUE = (76, 167, 255)
MENU_YELLOW = (255, 211, 61)
HUD_BLUE = (100, 181, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LOSE_BG = (29, 29, 29)
GREEN = (54, 201, 90)
GREEN_HOVER = (80, 226, 113)
RED = (201, 74, 74)
RED_HOVER = (224, 94, 94)

PLAYER_TARGET_SCREEN_ROW = 3
VISIBLE_BUFFER_ROWS = 3
FPS = 60


class CrossTheRoadGame:
    def __init__(self):
        pygame.init()
        self.audio_enabled = True
        try:
            pygame.mixer.init()
        except pygame.error:
            self.audio_enabled = False
        pygame.display.set_caption("Cross the Road")
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.base_dir = Path(__file__).resolve().parent
        self.assets_dir = self.base_dir / "assets"

        self.screen_width, self.screen_height = self.screen.get_size()
        self.row_height = max(100, self.screen_height // 7)
        self.move_x = max(50, self.row_height // 2)
        self.player_pixel = max(7, self.row_height // 11)
        self.player_width = self.player_pixel * 6
        self.player_height = self.player_pixel * 8
        self.car_pixel = max(8, self.row_height // 12)
        self.car_width = self.car_pixel * 16
        self.car_height = self.car_pixel * 7
        self.bottom_player_y = self.screen_height - self.row_height + (self.row_height - self.player_height) // 2
        self.player_screen_y_locked = (
            self.screen_height
            - ((PLAYER_TARGET_SCREEN_ROW + 1) * self.row_height)
            + (self.row_height - self.player_height) // 2
        )
        self.lane_offsets = (
            self.row_height // 4,
            (self.row_height * 3) // 5,
        )

        self.title_font = pygame.font.SysFont("couriernew", max(32, self.screen_width // 28), bold=True)
        self.menu_font = pygame.font.SysFont("couriernew", max(28, self.screen_width // 35), bold=True)
        self.info_font = pygame.font.SysFont("couriernew", max(16, self.screen_width // 70), bold=True)
        self.score_font = pygame.font.SysFont("couriernew", max(22, self.screen_width // 70), bold=True)
        self.help_font = pygame.font.SysFont("couriernew", max(16, self.screen_width // 95), bold=True)
        self.lose_font = pygame.font.SysFont("couriernew", max(36, self.screen_width // 32), bold=True)
        self.lose_small_font = pygame.font.SysFont("couriernew", max(20, self.screen_width // 60), bold=True)
        self.button_font = pygame.font.SysFont("couriernew", max(18, self.screen_width // 70), bold=True)

        self.load_audio()
        self.load_icon()
        self.state = "menu"
        self.play_button = self.make_center_button(int(self.screen_height * 0.48), max(260, self.screen_width // 5), max(120, self.screen_height // 6))
        self.restart_button = pygame.Rect(0, 0, max(280, self.screen_width // 5), max(90, self.screen_height // 11))
        self.close_button = pygame.Rect(0, 0, max(280, self.screen_width // 5), max(90, self.screen_height // 11))
        self.position_end_buttons()

        self.reset_game()

    def load_icon(self):
        icon_path = self.assets_dir / "game_icon.png"
        if icon_path.exists():
            try:
                icon_surface = pygame.image.load(str(icon_path)).convert_alpha()
                pygame.display.set_icon(icon_surface)
            except pygame.error:
                pass

    def load_audio(self):
        self.jump_sound = None
        self.score_sound = None
        self.music_started = False
        if not self.audio_enabled:
            return

        try:
            jump_path = self.assets_dir / "jump.wav"
            score_path = self.assets_dir / "score.wav"
            music_path = self.assets_dir / "bg_music.wav"

            if jump_path.exists():
                self.jump_sound = pygame.mixer.Sound(str(jump_path))
                self.jump_sound.set_volume(0.28)
            if score_path.exists():
                self.score_sound = pygame.mixer.Sound(str(score_path))
                self.score_sound.set_volume(0.34)
            if music_path.exists():
                pygame.mixer.music.load(str(music_path))
                pygame.mixer.music.set_volume(0.22)
                pygame.mixer.music.play(-1)
                self.music_started = True
        except pygame.error:
            self.jump_sound = None
            self.score_sound = None
            self.music_started = False

    def play_jump_sound(self):
        if self.jump_sound is not None:
            self.jump_sound.play()

    def play_score_sound(self):
        if self.score_sound is not None:
            self.score_sound.play()

    def make_center_button(self, y, width, height):
        x = (self.screen_width - width) // 2
        return pygame.Rect(x, y, width, height)

    def position_end_buttons(self):
        self.restart_button.center = (self.screen_width // 2, int(self.screen_height * 0.56) - 10)
        self.close_button.center = (self.screen_width // 2, int(self.screen_height * 0.70) - 10)

    def reset_game(self):
        self.player_x = self.screen_width // 2 - self.player_width // 2
        self.player_row = 0
        self.camera_row = 0
        self.score = 0
        self.max_completed_roads = 0
        self.rows = {0: {"kind": "sidewalk", "road_id": 0}}
        self.next_row_to_generate = 1
        self.next_road_id = 1
        self.cars_by_row = {}
        self.ensure_world_ready(self.max_visible_row())

    def max_visible_row(self):
        return self.camera_row + (self.screen_height // self.row_height) + VISIBLE_BUFFER_ROWS

    def current_difficulty_level(self):
        return self.score // 100

    def choose_lane_count(self):
        rng = random.Random(self.next_road_id * 149 + self.score * 17)
        if self.score < 1000:
            return 1 if rng.random() < 0.45 else 2
        if rng.random() < 0.35:
            return 4
        return 1 if rng.random() < 0.25 else 2

    def add_road_group(self):
        lane_count = self.choose_lane_count()
        road_id = self.next_road_id
        road_seed = road_id * 163 + lane_count * 29
        base_direction = 1 if random.Random(road_seed).random() < 0.5 else -1

        for lane_index in range(lane_count):
            direction = base_direction if lane_index % 2 == 0 else -base_direction
            self.rows[self.next_row_to_generate] = {
                "kind": "lane",
                "road_id": road_id,
                "lane_index": lane_index,
                "lane_count": lane_count,
                "direction": direction,
            }
            self.next_row_to_generate += 1

        self.rows[self.next_row_to_generate] = {
            "kind": "sidewalk",
            "road_id": road_id,
            "lane_count": lane_count,
            "is_finish": True,
        }
        self.next_row_to_generate += 1
        self.next_road_id += 1

    def ensure_world_ready(self, max_row):
        while self.next_row_to_generate <= max_row + VISIBLE_BUFFER_ROWS:
            self.add_road_group()

    def row_info(self, row_number):
        if row_number < 0:
            return {"kind": "sidewalk", "road_id": 0}
        self.ensure_world_ready(row_number)
        return self.rows[row_number]

    def row_type(self, row_number):
        return self.row_info(row_number)["kind"]

    def lane_direction(self, row_number):
        return self.row_info(row_number).get("direction", 1)

    def lane_speed(self, row_number):
        base_speed = self.car_pixel * (0.19 + (row_number % 5) * 0.028)
        return base_speed * (1.05 ** (self.score // 100))

    def lane_spacing_range(self, row_number):
        lane_info = self.row_info(row_number)
        lane_count = lane_info.get("lane_count", 1)
        difficulty_level = self.current_difficulty_level()
        easy_bonus = max(0, 95 - difficulty_level * 8)
        tighten_amount = min(110, difficulty_level * 6)
        lane_bonus = 120 if lane_count == 1 else 55

        if lane_count == 4:
            if self.score < 1200:
                lane_bonus += 95
            else:
                lane_bonus += max(30, 95 - (difficulty_level - 10) * 10)

        min_spacing = self.car_width + 170 + easy_bonus + lane_bonus - tighten_amount
        max_spacing = self.car_width + 300 + easy_bonus + lane_bonus - tighten_amount
        tightest_allowed = self.car_width + self.move_x + 22
        min_spacing = max(tightest_allowed, min_spacing)
        max_spacing = max(min_spacing + 55, max_spacing)
        return min_spacing, max_spacing

    def generate_cars_for_row(self, row_number):
        if self.row_type(row_number) != "lane" or row_number in self.cars_by_row:
            return

        rng = random.Random(row_number * 113 + 31)
        direction = self.lane_direction(row_number)
        min_spacing, max_spacing = self.lane_spacing_range(row_number)
        spacing = rng.randint(min_spacing, max_spacing)
        car_count = max(3, self.screen_width // spacing + 2)
        start_shift = rng.randint(0, spacing)
        cars = []

        for index in range(car_count):
            car_x = start_shift + index * spacing
            if direction == -1:
                car_x += self.car_width // 2
            cars.append(
                {
                    "x": float(car_x),
                    "color": rng.choice(
                        [
                            (224, 80, 80),
                            (78, 134, 228),
                            (230, 177, 61),
                            (87, 190, 112),
                        ]
                    ),
                }
            )

        self.cars_by_row[row_number] = cars

    def ensure_rows_ready(self, min_row, max_row):
        self.ensure_world_ready(max_row)
        for row_number in range(min_row, max_row + 1):
            self.generate_cars_for_row(row_number)

    def trim_old_rows(self):
        keep_min = self.camera_row - 8
        keep_max = self.max_visible_row() + 8
        rows_to_remove = [row for row in self.cars_by_row if row < keep_min or row > keep_max]
        for row in rows_to_remove:
            del self.cars_by_row[row]

    def row_screen_y(self, row_number):
        return self.screen_height - ((row_number - self.camera_row + 1) * self.row_height)

    def player_screen_y(self):
        if self.player_row <= PLAYER_TARGET_SCREEN_ROW:
            return self.bottom_player_y - (self.player_row * self.row_height)
        return self.player_screen_y_locked

    def update_camera(self):
        self.camera_row = max(0, self.player_row - PLAYER_TARGET_SCREEN_ROW)

    def update_score(self):
        row_info = self.row_info(self.player_row)
        if row_info["kind"] == "sidewalk":
            completed_roads = row_info.get("road_id", 0)
            if completed_roads > 0 and completed_roads > self.max_completed_roads:
                self.max_completed_roads = completed_roads
                self.score += 100
                self.play_score_sound()

    def move_player(self, key):
        moved_up = False

        if key == pygame.K_w:
            self.player_row += 1
            moved_up = True
        elif key == pygame.K_s:
            self.player_row = max(0, self.player_row - 1)
        elif key == pygame.K_a:
            self.player_x -= self.move_x
        elif key == pygame.K_d:
            self.player_x += self.move_x
        else:
            return

        self.play_jump_sound()
        self.player_x = max(0, min(self.screen_width - self.player_width, self.player_x))

        if moved_up:
            self.update_score()

        self.update_camera()
        self.ensure_rows_ready(self.camera_row - VISIBLE_BUFFER_ROWS, self.max_visible_row())
        self.trim_old_rows()
        self.check_collision()

    def move_cars(self):
        self.ensure_rows_ready(self.camera_row - VISIBLE_BUFFER_ROWS, self.max_visible_row())

        for row_number, cars in self.cars_by_row.items():
            if self.row_type(row_number) != "lane":
                continue

            direction = self.lane_direction(row_number)
            speed = self.lane_speed(row_number)

            for car in cars:
                car["x"] += speed * direction

                if direction == 1 and car["x"] > self.screen_width + self.car_width + 100:
                    car["x"] = -self.car_width - 160
                elif direction == -1 and car["x"] < -self.car_width - 160:
                    car["x"] = self.screen_width + 160

    def player_bounds(self):
        y = self.player_screen_y()
        return pygame.Rect(
            int(self.player_x + self.player_pixel),
            int(y + self.player_pixel),
            int(self.player_width - self.player_pixel * 2),
            int(self.player_height - self.player_pixel - 2),
        )

    def check_collision(self):
        if self.row_type(self.player_row) != "lane":
            return

        cars = self.cars_by_row.get(self.player_row, [])
        player_rect = self.player_bounds()

        for car in cars:
            car_y = self.row_screen_y(self.player_row) + (self.row_height - self.car_height) // 2
            car_rect = pygame.Rect(int(car["x"]), int(car_y), self.car_width, self.car_height)
            if player_rect.colliderect(car_rect):
                self.state = "lose"
                return

    def draw_pixel_rect(self, x, y, pixel_size, pixel_map, colors):
        for row_index, row_data in enumerate(pixel_map):
            for col_index, color_key in enumerate(row_data):
                if color_key == ".":
                    continue
                color = colors[color_key]
                rect = pygame.Rect(
                    int(x + col_index * pixel_size),
                    int(y + row_index * pixel_size),
                    int(pixel_size),
                    int(pixel_size),
                )
                pygame.draw.rect(self.screen, color, rect)

    def draw_text_center(self, text, font, color, center):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=center)
        self.screen.blit(surface, rect)

    def draw_button(self, rect, text, fill_color, hover_color, font):
        mouse_pos = pygame.mouse.get_pos()
        color = hover_color if rect.collidepoint(mouse_pos) else fill_color
        pygame.draw.rect(self.screen, color, rect, border_radius=40)
        pygame.draw.rect(self.screen, (212, 170, 27), rect, width=5, border_radius=40)
        self.draw_text_center(text, font, BLACK, rect.center)

    def draw_player(self, x, y):
        pixel_map = [
            "..HH..",
            ".HFFH.",
            ".HFFH.",
            "..SS..",
            ".JTTJ.",
            ".JTTJ.",
            ".P..P.",
            ".P..P.",
        ]
        colors = {
            "H": (42, 42, 42),
            "F": (242, 195, 139),
            "S": (69, 196, 90),
            "J": (31, 142, 57),
            "T": (59, 114, 216),
            "P": (112, 74, 46),
        }
        self.draw_pixel_rect(x, y, self.player_pixel, pixel_map, colors)

    def draw_car(self, x, y, body_color):
        pixel_map = [
            "...WWWWWWWWWW...",
            "..WBBBBBBBBBBBW.",
            ".WBBBBBBBBBBBBBW",
            "WBBBBBBBBBBBBBBW",
            "WBBBBBBBBBBBBBBW",
            ".KKBBBB....BBKK.",
            "..KKKK....KKKK..",
        ]
        colors = {
            "W": (221, 241, 255),
            "B": body_color,
            "K": (17, 17, 17),
        }
        self.draw_pixel_rect(x, y, self.car_pixel, pixel_map, colors)

    def draw_tree(self, x, y):
        trunk_width = max(10, self.player_pixel)
        trunk_height = max(18, self.player_pixel * 2)
        leaf_size = max(18, self.player_pixel * 2)

        pygame.draw.rect(self.screen, (107, 67, 40), (x, y + leaf_size, trunk_width, trunk_height))
        pygame.draw.rect(
            self.screen,
            (47, 163, 74),
            (x - leaf_size // 2, y + leaf_size // 3, trunk_width + leaf_size, leaf_size),
        )
        pygame.draw.rect(
            self.screen,
            (69, 196, 90),
            (x - leaf_size // 3, y, trunk_width + (leaf_size * 2) // 3, leaf_size),
        )

    def draw_lamp(self, x, y):
        pole_width = max(6, self.player_pixel - 1)
        pole_height = max(38, self.row_height // 3)
        lamp_width = max(20, self.player_pixel * 2)

        pygame.draw.rect(self.screen, (44, 44, 44), (x, y, pole_width, pole_height))
        pygame.draw.rect(
            self.screen,
            (255, 216, 106),
            (x - lamp_width // 2 + pole_width // 2, y - 12, lamp_width, 16),
        )
        pygame.draw.rect(self.screen, (89, 89, 89), (x - 10, y + pole_height, pole_width + 20, 8))

    def draw_flower_patch(self, x, y):
        petal = max(4, self.player_pixel - 2)
        pygame.draw.rect(self.screen, (255, 125, 183), (x, y, petal, petal))
        pygame.draw.rect(self.screen, (255, 241, 118), (x + petal, y - petal, petal, petal))
        pygame.draw.rect(self.screen, (255, 125, 183), (x + petal * 2, y, petal, petal))
        pygame.draw.rect(self.screen, (93, 174, 63), (x + petal, y, petal, petal))

    def draw_sidewalk_decor(self, row_number, y):
        seed = random.Random(row_number * 191 + 77)
        decor_count = 2 if self.screen_width < 1400 else 3
        edge_padding = max(50, self.screen_width // 20)
        safe_middle_left = self.screen_width // 2 - self.screen_width // 6
        safe_middle_right = self.screen_width // 2 + self.screen_width // 6

        for index in range(decor_count):
            side_left = index % 2 == 0
            if side_left:
                x = seed.randint(edge_padding, max(edge_padding + 10, safe_middle_left - 70))
            else:
                x = seed.randint(
                    min(self.screen_width - edge_padding - 70, safe_middle_right + 20),
                    self.screen_width - edge_padding,
                )

            choice = seed.choice(["lamp", "tree", "flowers"])
            if choice == "lamp":
                self.draw_lamp(x, y + self.row_height // 2 - 20)
            elif choice == "tree":
                self.draw_tree(x, y + self.row_height // 2 - 24)
            else:
                self.draw_flower_patch(x, y + self.row_height // 2)

    def draw_rows(self):
        min_row = max(0, self.camera_row - VISIBLE_BUFFER_ROWS)
        max_row = self.max_visible_row()

        for row_number in range(min_row, max_row + 1):
            y = self.row_screen_y(row_number)
            row_type = self.row_type(row_number)
            fill_color = BACKGROUND_COLOR if row_type == "sidewalk" else ROAD_COLOR
            pygame.draw.rect(self.screen, fill_color, (0, y, self.screen_width, self.row_height))

            if row_type == "lane":
                stripe_height = max(8, self.row_height // 12)
                stripe_width = max(80, self.screen_width // 12)
                stripe_gap = max(70, self.screen_width // 18)

                for offset in self.lane_offsets:
                    stripe_y = y + offset
                    x = 30
                    while x < self.screen_width:
                        pygame.draw.rect(self.screen, STRIPE_COLOR, (x, stripe_y, stripe_width, stripe_height))
                        x += stripe_width + stripe_gap
            else:
                self.draw_sidewalk_decor(row_number, y)

    def draw_cars(self):
        min_row = max(0, self.camera_row - VISIBLE_BUFFER_ROWS)
        max_row = self.max_visible_row()

        for row_number in range(min_row, max_row + 1):
            if self.row_type(row_number) != "lane":
                continue
            row_y = self.row_screen_y(row_number) + (self.row_height - self.car_height) // 2
            for car in self.cars_by_row.get(row_number, []):
                if -self.car_width <= car["x"] <= self.screen_width + self.car_width:
                    self.draw_car(car["x"], row_y, car["color"])

    def draw_hud_box(self, text, rect, font, align_right=False):
        pygame.draw.rect(self.screen, HUD_BLUE, rect)
        pygame.draw.rect(self.screen, WHITE, rect, width=4)
        text_surface = font.render(text, True, BLACK)
        if align_right:
            text_rect = text_surface.get_rect(midright=(rect.right - 20, rect.centery))
        else:
            text_rect = text_surface.get_rect(midleft=(rect.left + 20, rect.centery))
        self.screen.blit(text_surface, text_rect)

    def draw_hud(self):
        score_text = f"SCORE {self.score}"
        score_width = max(220, len(score_text) * (self.score_font.get_height() // 2 + 10))
        score_rect = pygame.Rect(22, 20, score_width, self.score_font.get_height() + 28)
        self.draw_hud_box(score_text, score_rect, self.score_font)

        help_text = "'ESC' = EXIT THE GAME"
        help_width = max(360, len(help_text) * (self.help_font.get_height() // 2 + 9))
        help_rect = pygame.Rect(self.screen_width - help_width - 24, 20, help_width, self.help_font.get_height() + 28)
        self.draw_hud_box(help_text, help_rect, self.help_font, align_right=True)

    def draw_menu(self):
        self.screen.fill(MENU_BLUE)
        self.draw_text_center("CROSS THE ROAD!", self.title_font, WHITE, (self.screen_width // 2, int(self.screen_height * 0.28)))
        pygame.draw.ellipse(self.screen, MENU_YELLOW, self.play_button)
        pygame.draw.ellipse(self.screen, (212, 170, 27), self.play_button, width=6)
        self.draw_text_center("PLAY", self.menu_font, BLACK, self.play_button.center)
        self.draw_text_center(
            "Click PLAY to start",
            self.info_font,
            (234, 244, 255),
            (self.screen_width // 2, int(self.screen_height * 0.72)),
        )

    def draw_game(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_rows()
        self.draw_cars()
        self.draw_player(self.player_x, self.player_screen_y())
        self.draw_hud()

    def draw_lose_screen(self):
        self.draw_game()
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        panel_width = max(420, self.screen_width // 3)
        panel_height = max(320, self.screen_height // 2)
        panel = pygame.Rect(0, 0, panel_width, panel_height)
        panel.center = (self.screen_width // 2, self.screen_height // 2)

        pygame.draw.rect(self.screen, LOSE_BG, panel, border_radius=24)
        pygame.draw.rect(self.screen, WHITE, panel, width=4, border_radius=24)

        self.draw_text_center("U LOST!", self.lose_font, WHITE, (panel.centerx, panel.top + 80))
        self.draw_text_center(f"Score: {self.score}", self.lose_small_font, (221, 221, 221), (panel.centerx, panel.top + 150))

        self.draw_button(self.restart_button, "RESTART", GREEN, GREEN_HOVER, self.button_font)
        self.draw_button(self.close_button, "CLOSE GAME", RED, RED_HOVER, self.button_font)

    def handle_menu_click(self, mouse_pos):
        if self.play_button.collidepoint(mouse_pos):
            self.reset_game()
            self.state = "playing"

    def handle_lose_click(self, mouse_pos):
        if self.restart_button.collidepoint(mouse_pos):
            self.reset_game()
            self.state = "playing"
        elif self.close_button.collidepoint(mouse_pos):
            self.quit_game()

    def quit_game(self):
        pygame.quit()
        sys.exit()

    def update(self):
        if self.state == "playing":
            self.move_cars()
            self.check_collision()

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
        else:
            self.draw_lose_screen()
        pygame.display.flip()

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.quit_game()
                    elif self.state == "playing":
                        self.move_player(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "menu":
                        self.handle_menu_click(event.pos)
                    elif self.state == "lose":
                        self.handle_lose_click(event.pos)

            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    CrossTheRoadGame().run()
