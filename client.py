import pygame
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

# Constants
WEBSOCKET_URL = "ws://localhost:8000/ws"
API_URL = "http://localhost:8000"

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BROWN = (139, 69, 19)
GRAY = (169, 169, 169)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
SKIN = (245, 222, 179)

# Global queues and flag for thread communication
update_queue = queue.Queue()
position_queue = queue.Queue()
collect_queue = queue.Queue()
exit_flag = False

# Assign a unique player ID
PLAYER_ID = "Player" + str(random.randint(1000, 9999))

# --- Communication Functions ---
def send_position_update(x, y):
    try:
        requests.post(f"{API_URL}/update-position/", json={"player": PLAYER_ID, "x": x, "y": y})
    except requests.RequestException as e:
        print(f"Error updating position: {e}")

def send_collect(crate_id):
    try:
        requests.post(f"{API_URL}/collect-item/", json={"player": PLAYER_ID, "item": crate_id})
    except requests.RequestException as e:
        print(f"Error collecting crate: {e}")

def communication_thread_func():
    while not exit_flag:
        try:
            while not position_queue.empty():
                x, y = position_queue.get()
                send_position_update(x, y)
            while not collect_queue.empty():
                crate_id = collect_queue.get()
                send_collect(crate_id)
            time.sleep(0.05)
        except Exception as e:
            print(f"Communication thread error: {e}")

# --- WebSocket Client ---
async def connect_to_server():
    global exit_flag
    backoff = 5
    while not exit_flag:
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                backoff = 5
                while not exit_flag:
                    data = await websocket.recv()
                    update_queue.put(loads(data))
        except Exception as e:
            if exit_flag:
                break
            print(f"WebSocket error: {e}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

# --- Game Classes and Functions ---
class Player:
    def __init__(self, x, y, speed=5):
        self.x = x
        self.y = y
        self.speed = speed
        self.held_item = None

    def get_rect(self):
        return pygame.Rect(self.x - 15, self.y - 12, 30, 50)

    def move(self, keys, screen_width, screen_height):
        if keys[pygame.K_LEFT]:
            self.x = max(30, self.x - self.speed)
        if keys[pygame.K_RIGHT]:
            self.x = min(screen_width - 30, self.x + self.speed)
        if keys[pygame.K_UP]:
            self.y = max(30, self.y - self.speed)
        if keys[pygame.K_DOWN]:
            self.y = min(screen_height - 30, self.y + self.speed)

def draw_player(screen, x, y, frame):
    # Head and face
    pygame.draw.circle(screen, SKIN, (x, y), 12)
    pygame.draw.circle(screen, BLACK, (x - 4, y - 2), 2)
    pygame.draw.circle(screen, BLACK, (x + 4, y - 2), 2)
    pygame.draw.line(screen, RED, (x - 4, y + 4), (x + 4, y + 4), 2)
    # Body with breathing animation
    body_height = 30 + (2 if frame % 20 < 10 else 0)
    pygame.draw.rect(screen, BLUE, (x - 8, y + 12, 16, body_height - 12))
    # Arms animation
    if frame % 20 < 10:
        pygame.draw.line(screen, SKIN, (x - 8, y + 15), (x - 20, y + 30), 3)
        pygame.draw.line(screen, SKIN, (x + 8, y + 15), (x + 20, y + 30), 3)
    else:
        pygame.draw.line(screen, SKIN, (x - 8, y + 15), (x - 15, y + 25), 3)
        pygame.draw.line(screen, SKIN, (x + 8, y + 15), (x + 15, y + 25), 3)
    # Legs animation
    if frame % 20 < 10:
        pygame.draw.line(screen, BLACK, (x - 4, y + body_height), (x - 12, y + 50), 3)
        pygame.draw.line(screen, BLACK, (x + 4, y + body_height), (x + 12, y + 50), 3)
    else:
        pygame.draw.line(screen, BLACK, (x - 4, y + body_height), (x - 8, y + 50), 3)
        pygame.draw.line(screen, BLACK, (x + 4, y + body_height), (x + 16, y + 50), 3)

def draw_warehouse(screen, width, height):
    screen.fill(GRAY)
    # Walls
    pygame.draw.rect(screen, BLACK, (0, 0, width, 20))
    pygame.draw.rect(screen, BLACK, (0, height - 20, width, 20))
    pygame.draw.rect(screen, BLACK, (0, 0, 20, height))
    pygame.draw.rect(screen, BLACK, (width - 20, 0, 20, height))
    # Floor pattern
    for i in range(0, width, 40):
        for j in range(0, height, 40):
            pygame.draw.rect(screen, GREEN, (i, j, 20, 20), 1)

def draw_menu(screen, font, menu_options, selected_option, username, signed_in):
    screen.fill(BLACK)
    title = font.render("WAREHOUSE EXPLORER", True, WHITE)
    screen.blit(title, (400 - title.get_width()//2, 100))
    for i, option in enumerate(menu_options):
        color = WHITE if i == selected_option else GRAY
        text = font.render(option, True, color)
        screen.blit(text, (400 - text.get_width()//2, 250 + i * 50))
    if signed_in:
        welcome = font.render(f"Welcome, {username}!", True, WHITE)
        screen.blit(welcome, (400 - welcome.get_width()//2, 450))

def main():
    global exit_flag
    pygame.init()
    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Warehouse Explorer - Retro Edition")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)

    menu_options = ["Sign In", "Start Game", "Quit"]
    selected_option = 0
    in_menu = True
    signed_in = False
    username = ""
    player = Player(screen_width//2, screen_height//2)
    animation_frame = 0

    # Start communication thread (for REST API calls)
    comm_thread = threading.Thread(target=communication_thread_func, daemon=True)
    comm_thread.start()

    # Start websocket connection in an asyncio thread
    loop = asyncio.new_event_loop()
    asyncio_thread = threading.Thread(target=loop.run_until_complete, args=(connect_to_server(),), daemon=True)
    asyncio_thread.start()

    # Local state for crates received from the server
    crates = {}  # { crate_id: {"x":, "y":, "state":, "player":} }
    
    # Define delivery zone (for delivering carried crates)
    delivery_zone = pygame.Rect(400, 500, 100, 50)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                exit_flag = True
            if in_menu:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected_option = (selected_option - 1) % len(menu_options)
                    elif event.key == pygame.K_DOWN:
                        selected_option = (selected_option + 1) % len(menu_options)
                    elif event.key == pygame.K_RETURN:
                        if selected_option == 0 and not signed_in:
                            username = PLAYER_ID  # auto assign ID
                            signed_in = True
                        elif selected_option == 1 and signed_in:
                            in_menu = False
                        elif selected_option == 2:
                            running = False
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        in_menu = True
                    elif event.key == pygame.K_SPACE:
                        # Attempt to pick up a nearby crate
                        player_rect = player.get_rect()
                        for crate_id, crate in crates.items():
                            crate_rect = pygame.Rect(crate["x"], crate["y"], 40, 40)
                            if crate["state"] == "on_floor" and player_rect.colliderect(crate_rect):
                                player.held_item = crate_id
                                collect_queue.put(crate_id)
                                break
                    elif event.key == pygame.K_d:
                        # Deliver held crate if within the delivery zone
                        if player.held_item and player.get_rect().colliderect(delivery_zone):
                            collect_queue.put(player.held_item)  # Deliver crate
                            player.held_item = None

        if in_menu:
            draw_menu(screen, font, menu_options, selected_option, username, signed_in)
        else:
            keys = pygame.key.get_pressed()
            player.move(keys, screen_width, screen_height)
            # Send position updates periodically
            position_queue.put((player.x, player.y))
            # Update local crates data from the websocket updates
            while not update_queue.empty():
                data = update_queue.get()
                crates = data.get("crates", {})

            animation_frame += 1

            draw_warehouse(screen, screen_width, screen_height)
            # Draw delivery zone
            pygame.draw.rect(screen, GREEN, delivery_zone)
            delivery_text = font.render("Delivery", True, BLACK)
            screen.blit(delivery_text, (delivery_zone.centerx - delivery_text.get_width()//2, delivery_zone.centery - 10))

            # Draw crates
            for crate in crates.values():
                if crate["state"] == "on_floor":
                    pygame.draw.rect(screen, BROWN, (crate["x"], crate["y"], 40, 40))
                elif crate["state"] == "carried" and crate["player"] == PLAYER_ID and player.held_item:
                    pygame.draw.rect(screen, BROWN, (player.x - 20, player.y - 40, 40, 40))

            # Draw player
            draw_player(screen, player.x, player.y, animation_frame)
            # Display held item info
            inv_text = font.render(f"Held: {player.held_item if player.held_item else 'None'}", True, WHITE)
            screen.blit(inv_text, (10, 10))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
# Run with: python client.py