import pygame as pg
import sys
import asyncio
import websockets
import json
from json import loads
import requests
import threading
import random
import queue
import time

# FastAPI Backend URLs
WEBSOCKET_URL = "ws://localhost:8000/ws"
API_URL = "http://localhost:8000"

# Colors (retro palette)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BROWN = (139, 69, 19)
GRAY = (169, 169, 169)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
SKIN = (245, 222, 179)  # Flesh tone for human look

# Global variables with thread-safe access
crates = {}
crates_lock = threading.Lock()
player_scores = {}
player_scores_lock = threading.Lock()
update_queue = queue.Queue()
position_queue = queue.Queue()
pick_up_queue = queue.Queue()
deliver_queue = queue.Queue()
exit_flag = False  # Global flag to signal exit

# Player info
PLAYER_ID = "Player" + str(random.randint(1, 1000))  # Unique identifier for this player

def send_position_update(x, y):
    """Send player position to the backend."""
    try:
        requests.post(f"{API_URL}/update-position/", json={"player": PLAYER_ID, "x": x, "y": y})
    except requests.RequestException as e:
        print(f"Error updating position: {e}")

def send_pick_up(crate_id):
    """Send a request to pick up a crate to the backend."""
    try:
        requests.post(f"{API_URL}/pick_up/", json={"player": PLAYER_ID, "crate_id": crate_id})
    except requests.RequestException as e:
        print(f"Error picking up crate: {e}")

def send_deliver(crate_id):
    """Send a request to deliver a crate to the backend."""
    try:
        requests.post(f"{API_URL}/deliver/", json={"player": PLAYER_ID, "crate_id": crate_id})
    except requests.RequestException as e:
        print(f"Error delivering crate: {e}")

def communication_thread_func():
    """Handle sending position updates, pick-up, and deliver requests in a separate thread."""
    while not exit_flag:
        try:
            while not position_queue.empty():
                x, y = position_queue.get()
                send_position_update(x, y)
            while not pick_up_queue.empty():
                crate_id = pick_up_queue.get()
                send_pick_up(crate_id)
            while not deliver_queue.empty():
                crate_id = deliver_queue.get()
                send_deliver(crate_id)
            time.sleep(0.01)  # Small sleep to avoid busy waiting
        except Exception as e:
            print(f"Communication thread error: {e}")

def draw_player(screen, rect, frame):
    """Draw a player with animation at the given rect position."""
    x = rect.centerx
    y = rect.y
    # Head with face
    pg.draw.circle(screen, SKIN, (x, y), 12)  # Head
    pg.draw.circle(screen, BLACK, (x - 4, y - 2), 2)  # Left eye
    pg.draw.circle(screen, BLACK, (x + 4, y - 2), 2)  # Right eye
    pg.draw.line(screen, RED, (x - 4, y + 4), (x + 4, y + 4), 2)  # Mouth
    # Body with shirt (breathing effect)
    body_height = 30 + (2 if frame % 20 < 10 else 0)
    pg.draw.rect(screen, BLUE, (x - 8, y + 12, 16, body_height - 12))  # Shirt
    # Arms (moving while walking)
    if frame % 20 < 10:
        pg.draw.line(screen, SKIN, (x - 8, y + 15), (x - 20, y + 30), 3)  # Left arm
        pg.draw.line(screen, SKIN, (x + 8, y + 15), (x + 20, y + 30), 3)  # Right arm
    else:
        pg.draw.line(screen, SKIN, (x - 8, y + 15), (x - 15, y + 25), 3)
        pg.draw.line(screen, SKIN, (x + 8, y + 15), (x + 15, y + 25), 3)
    # Legs with pants (simple walking animation)
    if frame % 20 < 10:
        pg.draw.line(screen, BLACK, (x - 4, body_height + y), (x - 12, y + 50), 3)  # Left leg
        pg.draw.line(screen, BLACK, (x + 4, body_height + y), (x + 12, y + 50), 3)  # Right leg
    else:
        pg.draw.line(screen, BLACK, (x - 4, body_height + y), (x - 8, y + 50), 3)
        pg.draw.line(screen, BLACK, (x + 4, body_height + y), (x + 16, y + 50), 3)

class Player:
    def __init__(self, x, y, width, height, speed):
        self.rect = pg.Rect(x, y, width, height)
        self.speed = speed

    def draw(self, screen, frame):
        draw_player(screen, self.rect, frame)

    def move(self, keys, screen_width, screen_height):
        if keys[pg.K_LEFT] and self.rect.x > 0:
            self.rect.x -= self.speed
        if keys[pg.K_RIGHT] and self.rect.x < screen_width - self.rect.width:
            self.rect.x += self.speed
        if keys[pg.K_UP] and self.rect.y > 0:
            self.rect.y -= self.speed
        if keys[pg.K_DOWN] and self.rect.y < screen_height - self.rect.height:
            self.rect.y += self.speed

class GameApp:
    def __init__(self):
        self.screen_width = 950
        self.screen_height = 600
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height))
        self.clock = pg.time.Clock()
        self.player = Player(self.screen_width // 2 - 10, self.screen_height - 70, 20, 50, speed=5)
        self.delivery_zone = pg.Rect(400, 500, 100, 50)
        self.other_players = {}
        self.start_time = time.time()
        self.last_position_send_time = time.time()
        self.animation_frame = 0
        self.crates_initialized = False
        self.init_time = time.time()
        try:
            self.crate_image = pg.image.load("assets/crate.png").convert_alpha()
        except FileNotFoundError:
            self.crate_image = pg.Surface((20, 20))
            self.crate_image.fill(BROWN)
        self.crate_image = pg.transform.scale(self.crate_image, (20, 20))

    def generate_new_crate_position(self):
        while True:
            new_rect = pg.Rect(random.randint(50, self.screen_width - 50), random.randint(50, self.screen_height - 100), 20, 20)
            overlaps = False
            with crates_lock:
                for crate_id, crate in crates.items():
                    if crate['state'] == 'on_floor' and new_rect.colliderect(pg.Rect(crate['position']['x'], crate['position']['y'], 20, 20)):
                        overlaps = True
                        break
            if not overlaps and not new_rect.colliderect(self.player.rect) and not new_rect.colliderect(self.delivery_zone):
                return new_rect

    def update_from_queue(self):
        while not update_queue.empty():
            data = update_queue.get()
            with crates_lock:
                crates.update(data.get("crates", {}))
                if crates and not self.crates_initialized:
                    self.crates_initialized = True
            self.other_players = {pid: pg.Rect(info["x"], info["y"], 20, 50) for pid, info in data.get("players", {}).items() if pid != PLAYER_ID}
            with player_scores_lock:
                player_scores.update(data.get("scores", {}))

    def run_game(self):
        pg.init()
        pg.display.set_caption("Warehouse Explorer - Multiplayer Edition")
        running = True
        font = pg.font.SysFont(None, 24)

        while running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                    global exit_flag
                    exit_flag = True
                    pg.quit()
                    sys.exit()
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_SPACE:  # Pick up crate
                        carrying_crate = next((cid for cid, c in crates.items() if c['state'] == 'carried' and c['carried_by'] == PLAYER_ID), None)
                        if carrying_crate is None:
                            nearby_crates = [cid for cid, c in crates.items() if c['state'] == 'on_floor' and self.player.rect.colliderect(pg.Rect(c['position']['x'], c['position']['y'], 20, 20))]
                            if nearby_crates:
                                pick_up_queue.put(nearby_crates[0])
                    elif event.key == pg.K_d:  # Deliver crate
                        carrying_crate = next((cid for cid, c in crates.items() if c['state'] == 'carried' and c['carried_by'] == PLAYER_ID), None)
                        if carrying_crate is not None and self.player.rect.colliderect(self.delivery_zone):
                            deliver_queue.put(carrying_crate)

            # Player movement
            keys = pg.key.get_pressed()
            self.player.move(keys, self.screen_width, self.screen_height)

            # Send position update periodically
            current_time = time.time()
            if current_time - self.last_position_send_time > 0.1:
                position_queue.put((self.player.rect.x, self.player.rect.y))
                self.last_position_send_time = current_time

            # Fallback mechanism: spawn crates if no data received within 5 seconds
            if current_time - self.init_time > 5 and not self.crates_initialized:
                with crates_lock:
                    crates.update({str(i): {"position": {"x": r.x, "y": r.y}, "state": "on_floor"} for i, r in enumerate([self.generate_new_crate_position() for _ in range(5)])})
                self.crates_initialized = True

            self.update_from_queue()
            self.animation_frame += 1

            # Drawing
            self.screen.fill(GRAY)  # Warehouse floor
            pg.draw.rect(self.screen, GREEN, self.delivery_zone)  # Delivery zone
            delivery_text = font.render("Delivery", True, BLACK)
            self.screen.blit(delivery_text, (self.delivery_zone.centerx - delivery_text.get_width() // 2, self.delivery_zone.centery - delivery_text.get_height() // 2))

            # Draw crates
            with crates_lock:
                for crate_id, crate in crates.items():
                    if crate['state'] == 'on_floor':
                        self.screen.blit(self.crate_image, (crate['position']['x'], crate['position']['y']))
                    elif crate['state'] == 'carried':
                        player_id = crate['carried_by']
                        if player_id == PLAYER_ID:
                            self.screen.blit(self.crate_image, (self.player.rect.x, self.player.rect.y - 20))
                        elif player_id in self.other_players:
                            self.screen.blit(self.crate_image, (self.other_players[player_id].x, self.other_players[player_id].y - 20))

            # Draw players
            self.player.draw(self.screen, self.animation_frame)
            for player_id, rect in self.other_players.items():
                draw_player(self.screen, rect, self.animation_frame)

            # Display game info
            time_remaining = max(0, 60 - (current_time - self.start_time))
            with player_scores_lock:
                score = player_scores.get(PLAYER_ID, 0)
            score_text = font.render(f"Score: {score}", True, WHITE)
            timer_text = font.render(f"Time: {time_remaining:.1f}s", True, WHITE)
            self.screen.blit(score_text, (10, 10))
            self.screen.blit(timer_text, (10, 40))

            # Game over condition
            if time_remaining <= 0:
                game_over_text = font.render("Game Over", True, RED)
                self.screen.blit(game_over_text, (self.screen_width // 2 - 50, self.screen_height // 2))
                pg.display.flip()
                pg.time.wait(2000)
                running = False

            pg.display.flip()
            self.clock.tick(60)

        pg.quit()

async def connect_to_server():
    """Connect to the WebSocket server and update game state."""
    global player_scores, exit_flag
    backoff = 5
    while not exit_flag:
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                backoff = 5
                while not exit_flag:
                    data = await websocket.recv()
                    data_json = loads(data)
                    update_queue.put(data_json)
        except websockets.exceptions.WebSocketException as e:
            if exit_flag:
                break
            print(f"Websockets error: {e}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

def run_game_app():
    """Run the Pygame application."""
    game_app = GameApp()
    game_app.run_game()

async def main():
    """Run Pygame in a thread and WebSocket in the main thread after verifying server connection."""
    try:
        async with websockets.connect(WEBSOCKET_URL):
            print("Server is reachable.")
    except websockets.exceptions.WebSocketException as e:
        print(f"Cannot connect to server: {e}")
        sys.exit(1)

    communication_thread = threading.Thread(target=communication_thread_func, daemon=True)
    communication_thread.start()
    game_thread = threading.Thread(target=run_game_app, daemon=False)
    game_thread.start()
    await connect_to_server()
    game_thread.join()

if __name__ == "__main__":
    asyncio.run(main())