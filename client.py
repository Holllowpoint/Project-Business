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

# Global variables with thread-safe access
items = {}
items_lock = threading.Lock()
player_scores = {}
player_scores_lock = threading.Lock()
update_queue = queue.Queue()
position_queue = queue.Queue()
collect_queue = queue.Queue()
exit_flag = False  # Global flag to signal exit

# Player info
PLAYER_ID = "Player1"  # Unique identifier for this player

def send_collect_item(item_name):
    """Send a request to collect an item to the backend."""
    try:
        response = requests.post(f"{API_URL}/collect-item/", json={"player": PLAYER_ID, "item": item_name})
        print(response.json())
    except requests.RequestException as e:
        print(f"Error collecting item: {e}")

def send_position_update(x, y):
    """Send player position to the backend."""
    try:
        requests.post(f"{API_URL}/update-position/", json={"player": PLAYER_ID, "x": x, "y": y})
    except requests.RequestException as e:
        print(f"Error updating position: {e}")

def communication_thread_func():
    """Handle sending position updates and item collection requests in a separate thread."""
    while not exit_flag:
        try:
            while not position_queue.empty():
                x, y = position_queue.get()
                send_position_update(x, y)
            while not collect_queue.empty():
                item_name = collect_queue.get()
                send_collect_item(item_name)
            time.sleep(0.01)  # Small sleep to avoid busy waiting
        except Exception as e:
            print(f"Communication thread error: {e}")

class Player:
    def __init__(self, x, y, width, height, speed):
        self.rect = pg.Rect(x, y, width, height)
        self.speed = speed

    def draw(self, screen):
        # Draw head
        pg.draw.circle(screen, (255, 255, 255), (self.rect.centerx, self.rect.y + 10), 10)
        # Draw body
        pg.draw.line(screen, (255, 255, 255), (self.rect.centerx, self.rect.y + 20), (self.rect.centerx, self.rect.y + 50), 2)
        # Draw arms
        pg.draw.line(screen, (255, 255, 255), (self.rect.centerx, self.rect.y + 30), (self.rect.centerx - 15, self.rect.y + 40), 2)
        pg.draw.line(screen, (255, 255, 255), (self.rect.centerx, self.rect.y + 30), (self.rect.centerx + 15, self.rect.y + 40), 2)
        # Draw legs
        pg.draw.line(screen, (255, 255, 255), (self.rect.centerx, self.rect.y + 50), (self.rect.centerx - 10, self.rect.y + 70), 2)
        pg.draw.line(screen, (255, 255, 255), (self.rect.centerx, self.rect.y + 50), (self.rect.centerx + 10, self.rect.y + 70), 2)

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
        self.player = Player(self.screen_width // 2 - 20, self.screen_height - 70, 40, 60, speed=5)  # Increased speed to 40
        self.initial_player_rect = self.player.rect.copy()
        try:
            self.crate_image = pg.image.load("assets/crate.png").convert_alpha()
        except FileNotFoundError:
            self.crate_image = pg.Surface((20, 20))
            self.crate_image.fill((139, 69, 19))
        self.crate_image = pg.transform.scale(self.crate_image, (20, 20))
        self.other_players = {}
        self.inventory = {}
        self.initial_crate_count = 0
        self.start_time = time.time()
        self.init_time = time.time()  # Time when game starts
        self.crates_initialized = False  # Flag for crate initialization
        self.last_fps_update = time.time()
        self.display_fps = 0
        self.last_position_send_time = time.time()
        pg.mixer.init()
        try:
            pg.mixer.music.load("assets/Reflections on the Water.mp3")
        except pg.error:
            print("Music file not found. Using placeholder sound.")
            pg.mixer.music.load(self.create_placeholder_sound())

    def create_placeholder_sound(self):
        import wave
        import struct
        filename = "assets/placeholder.wav"
        sample_rate = 44100
        duration = 5
        frequency = 440
        with wave.open(filename, 'w') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            for i in range(sample_rate * duration):
                value = int(32767.0 * 0.5 * (1 + (i // (sample_rate // 2)) % 2))
                data = struct.pack('<h', value)
                f.writeframesraw(data)
        return filename

    def generate_new_crate_position(self):
        while True:
            new_rect = pg.Rect(random.randint(50, self.screen_width - 50), random.randint(50, self.screen_height - 50), 20, 20)
            overlaps = False
            with items_lock:
                for item_name, rect_list in items.items():
                    for rect, _ in rect_list:
                        if new_rect.colliderect(rect):
                            overlaps = True
                            break
                    if overlaps:
                        break
            if not overlaps and not new_rect.colliderect(self.initial_player_rect):
                return new_rect

    def check_item_collection(self):
        with items_lock:
            items_copy = {item_name: [(rect, collected) for rect, collected in rect_list] for item_name, rect_list in items.items()}
        for item_name, rect_list in items_copy.items():
            for rect, collected in rect_list:
                if not collected and self.player.rect.colliderect(rect):
                    collect_queue.put(item_name)
                    with items_lock:
                        for i, (r, c) in enumerate(items[item_name]):
                            if r == rect:
                                items[item_name][i] = (r, True)
                    break

    def update_from_queue(self):
        while not update_queue.empty():
            data = update_queue.get()
            print("Received server data:", data)  # Debug print
            inv_data = data.get("inventory", {})
            with items_lock:
                for item_name, count in inv_data.items():
                    if count > 0:
                        if item_name not in items:
                            items[item_name] = [(self.generate_new_crate_position(), False) for _ in range(count)]
                            print(f"Added {count} {item_name} from server.")
                        self.crates_initialized = True

    def run_game(self):
        pg.init()
        pg.display.set_caption("Warehouse Explorer - Retro Edition")
        running = True
        font = pg.font.SysFont(None, 24)
        pg.mixer.music.play(-1)
        while running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                    pg.mixer.music.fadeout(1000)
                    global exit_flag
                    exit_flag = True
                    pg.quit()
                    sys.exit()

            keys = pg.key.get_pressed()
            self.player.move(keys, self.screen_width, self.screen_height)

            current_time = time.time()
            if current_time - self.last_position_send_time > 0.1:
                position_queue.put((self.player.rect.x, self.player.rect.y))
                self.last_position_send_time = current_time

            # Fallback mechanism: spawn default crates if no data received within 5 seconds
            if current_time - self.init_time > 5 and not self.crates_initialized:
                print("Triggering fallback to spawn crates.")  # Debug print
                with items_lock:
                    items["crates"] = [(pg.Rect(random.randint(50, self.screen_width - 50), random.randint(50, self.screen_height - 50), 20, 20), False) for _ in range(10)]
                self.initial_crate_count = 10
                self.crates_initialized = True
                print("Number of crates added:", len(items["crates"]))  # Debug print

            self.check_item_collection()
            self.update_from_queue()

            self.screen.fill((0, 0, 0))
            self.player.draw(self.screen)

            for player_id, rect in self.other_players.items():
                pg.draw.rect(self.screen, (0, 255, 0), rect, 2)

            with items_lock:
                items_copy = {item_name: [(rect, collected) for rect, collected in rect_list] for item_name, rect_list in items.items()}
            print("Current items:", items_copy)  # Debug print
            for item_name, rect_list in items_copy.items():
                image = self.crate_image
                for rect, collected in rect_list:
                    if collected:
                        dimmed_image = image.copy()
                        dimmed_image.set_alpha(100)
                        self.screen.blit(dimmed_image, rect)
                    else:
                        self.screen.blit(image, rect)

            if current_time - self.last_fps_update >= 5:
                self.display_fps = self.clock.get_fps()
                self.last_fps_update = current_time

            time_remaining = max(0, 30 - (current_time - self.start_time))
            with player_scores_lock:
                score = player_scores.get(PLAYER_ID, 0)
            crates_left = self.inventory.get("crates", 0)
            game_over = False
            result_text = None

            if time_remaining <= 0:
                game_over = True
                if crates_left == 0 and score == self.initial_crate_count * 10:
                    result_text = font.render("You Win!", True, (0, 255, 0))
                else:
                    result_text = font.render("Game Over", True, (255, 0, 0))

            # Display game info
            score_text = font.render(f"Score: {score}", True, (255, 255, 255))
            crates_text = font.render(f"Crates: {crates_left}", True, (255, 255, 255))
            fps_text = font.render(f"FPS: {self.display_fps:.1f}", True, (255, 255, 255))
            timer_text = font.render(f"Time: {time_remaining:.1f}s", True, (255, 255, 255))
            self.screen.blit(score_text, (10, 10))
            self.screen.blit(crates_text, (10, 40))
            self.screen.blit(fps_text, (10, 70))
            self.screen.blit(timer_text, (10, 100))
            if game_over and result_text:
                self.screen.blit(result_text, (self.screen_width // 2 - 50, self.screen_height // 2))

            pg.display.flip()
            self.clock.tick(60)  # Ensure consistent 60 FPS

            if game_over:
                pg.mixer.music.fadeout(1000)
                pg.time.wait(2000)
                running = False
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
                    with player_scores_lock:
                        player_scores.update(data_json.get("scores", {}))
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
    # Check if server is reachable before starting
    try:
        async with websockets.connect(WEBSOCKET_URL):
            print("Server is reachable.")
    except websockets.exceptions.WebSocketException as e:
        print(f"Cannot connect to server: {e}")
        print("Please start the server and try again.")
        sys.exit(1)

    # Start communication thread for non-blocking server requests
    communication_thread = threading.Thread(target=communication_thread_func, daemon=True)
    communication_thread.start()

    # Start game thread and WebSocket connection
    game_thread = threading.Thread(target=run_game_app, daemon=False)
    game_thread.start()
    await connect_to_server()
    game_thread.join()

if __name__ == "__main__":
    asyncio.run(main())