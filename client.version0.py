import pygame
import sys


# Initialize Pygame
pygame.init()


# Screen settings
WIDTH = 800
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Warehouse Explorer - Retro Edition")


# Colors (retro palette)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BROWN = (139, 69, 19)
GRAY = (169, 169, 169)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
SKIN = (245, 222, 179)  # Flesh tone for human look


# Player settings
player_x = WIDTH // 2
player_y = HEIGHT // 2
player_speed = 5
animation_frame = 0
breathing = True
direction = "right"
held_item = None  # Item being carried by the player


# Menu settings
menu_options = ["Sign In", "Start Game", "Quit"]
selected_option = 0
in_menu = True
signed_in = False
username = ""


# Stock Item class for warehouse crates
class StockItem:
    def __init__(self, name, weight, rect):
        self.name = name
        self.weight = weight
        self.rect = rect  # Pygame Rect object for position and size
        self.is_held = False
        self.on_shelf = None  # Reference to shelf if placed on one


# Warehouse items (crates)
warehouse_crates = [
    StockItem("Box of Nails", 2.5, pygame.Rect(150, 150, 40, 40)),
    StockItem("Hammer", 1.0, pygame.Rect(600, 400, 40, 40)),
    StockItem("Screws", 1.5, pygame.Rect(300, 200, 40, 40))
]


# Shelves
warehouse_shelves = [
    pygame.Rect(50, 50, 200, 20),   # Top shelf
    pygame.Rect(50, 250, 200, 20),  # Middle shelf
    pygame.Rect(550, 150, 200, 20)  # Right shelf
]


# Font for retro feel
font = pygame.font.Font(None, 36)


clock = pygame.time.Clock()


def draw_player(x, y, frame):
    # Head with face
    pygame.draw.circle(screen, SKIN, (x, y), 12)  # Head
    pygame.draw.circle(screen, BLACK, (x - 4, y - 2), 2)  # Left eye
    pygame.draw.circle(screen, BLACK, (x + 4, y - 2), 2)  # Right eye
    pygame.draw.line(screen, RED, (x - 4, y + 4), (x + 4, y + 4), 2)  # Mouth
   
    # Body with shirt (breathing effect)
    body_height = 30 + (2 if breathing and frame % 20 < 10 else 0)
    pygame.draw.rect(screen, BLUE, (x - 8, y + 12, 16, body_height - 12))  # Shirt
   
    # Arms (moving while walking)
    if frame % 20 < 10:
        pygame.draw.line(screen, SKIN, (x - 8, y + 15), (x - 20, y + 30), 3)  # Left arm
        pygame.draw.line(screen, SKIN, (x + 8, y + 15), (x + 20, y + 30), 3)  # Right arm
    else:
        pygame.draw.line(screen, SKIN, (x - 8, y + 15), (x - 15, y + 25), 3)
        pygame.draw.line(screen, SKIN, (x + 8, y + 15), (x + 15, y + 25), 3)
   
    # Legs with pants (walking animation)
    if direction in ["left", "right"]:
        if frame % 20 < 10:
            pygame.draw.line(screen, BLACK, (x - 4, y + body_height), (x - 12, y + 50), 3)  # Left leg
            pygame.draw.line(screen, BLACK, (x + 4, y + body_height), (x + 12, y + 50), 3)  # Right leg
        else:
            pygame.draw.line(screen, BLACK, (x - 4, y + body_height), (x - 8, y + 50), 3)
            pygame.draw.line(screen, BLACK, (x + 4, y + body_height), (x + 16, y + 50), 3)
    else:
        pygame.draw.line(screen, BLACK, (x - 4, y + body_height), (x - 8, y + 50), 3)
        pygame.draw.line(screen, BLACK, (x + 4, y + body_height), (x + 8, y + 50), 3)


def draw_warehouse():
    # Draw warehouse background
    screen.fill(GRAY)  # Floor
   
    # Walls
    pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, 20))  # Top wall
    pygame.draw.rect(screen, BLACK, (0, HEIGHT - 20, WIDTH, 20))  # Bottom wall
    pygame.draw.rect(screen, BLACK, (0, 0, 20, HEIGHT))  # Left wall
    pygame.draw.rect(screen, BLACK, (WIDTH - 20, 0, 20, HEIGHT))  # Right wall
   
    # Retro floor pattern
    for i in range(0, WIDTH, 40):
        for j in range(0, HEIGHT, 40):
            pygame.draw.rect(screen, GREEN, (i, j, 20, 20), 1)
   
    # Draw shelves
    for shelf in warehouse_shelves:
        pygame.draw.rect(screen, BROWN, shelf)
        pygame.draw.rect(screen, BLACK, shelf, 2)
        pygame.draw.line(screen, BLACK, (shelf.x, shelf.y), (shelf.x, shelf.y - 20), 2)
        pygame.draw.line(screen, BLACK, (shelf.x + shelf.width, shelf.y), (shelf.x + shelf.width, shelf.y - 20), 2)
   
    # Draw crates (only if not held)
    for crate in warehouse_crates:
        if not crate.is_held:
            pygame.draw.rect(screen, BROWN, crate.rect)
            pygame.draw.rect(screen, BLACK, crate.rect, 2)
            pygame.draw.line(screen, BLACK, (crate.rect.x, crate.rect.y), (crate.rect.x + 40, crate.rect.y + 40), 1)
            pygame.draw.line(screen, BLACK, (crate.rect.x + 40, crate.rect.y), (crate.rect.x, crate.rect.y + 40), 1)


def draw_menu():
    screen.fill(BLACK)
    title = font.render("WAREHOUSE EXPLORER", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
   
    for i, option in enumerate(menu_options):
        color = WHITE if i == selected_option else GRAY
        text = font.render(option, True, color)
        screen.blit(text, (WIDTH//2 - text.get_width()//2, 250 + i * 50))
   
    if signed_in:
        welcome = font.render(f"Welcome, {username}!", True, WHITE)
        screen.blit(welcome, (WIDTH//2 - welcome.get_width()//2, 450))


def draw_inventory():
    # Display inventory in the bottom left corner
    y_offset = HEIGHT - 120
    inventory_title = font.render("Inventory:", True, WHITE)
    screen.blit(inventory_title, (10, y_offset))
    y_offset += 30
    for crate in warehouse_crates:
        location = "Held" if crate.is_held else f"Shelf at ({crate.on_shelf.x}, {crate.on_shelf.y})" if crate.on_shelf else "Floor"
        text = font.render(f"{crate.name} - {location}", True, WHITE)
        screen.blit(text, (10, y_offset))
        y_offset += 20


def check_collision():
    player_rect = pygame.Rect(player_x - 15, player_y - 12, 30, 50)
    for item in warehouse_shelves:
        if player_rect.colliderect(item):
            return True
    return False


def pick_up_item():
    global held_item
    if held_item is None:
        player_rect = pygame.Rect(player_x - 15, player_y - 12, 30, 50)
        for crate in warehouse_crates:
            if player_rect.colliderect(crate.rect) and not crate.is_held:
                held_item = crate
                crate.is_held = True
                crate.on_shelf = None
                break


def drop_item():
    global held_item
    if held_item is not None:
        player_rect = pygame.Rect(player_x - 15, player_y - 12, 30, 50)
        for shelf in warehouse_shelves:
            if player_rect.colliderect(shelf):
                held_item.rect.x = shelf.x + 10  # Place on shelf
                held_item.rect.y = shelf.y - 40
                held_item.on_shelf = shelf
                held_item.is_held = False
                held_item = None
                return
        # If not near a shelf, drop on floor
        held_item.rect.x = player_x
        held_item.rect.y = player_y + 50
        held_item.is_held = False
        held_item.on_shelf = None
        held_item = None


# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
       
        if in_menu:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_option = (selected_option - 1) % len(menu_options)
                elif event.key == pygame.K_DOWN:
                    selected_option = (selected_option + 1) % len(menu_options)
                elif event.key == pygame.K_RETURN:
                    if selected_option == 0 and not signed_in:
                        username = "Player" + str(pygame.time.get_ticks() % 1000)
                        signed_in = True
                    elif selected_option == 1 and signed_in:
                        in_menu = False
                    elif selected_option == 2:
                        running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for i, option in enumerate(menu_options):
                    text = font.render(option, True, WHITE)
                    text_rect = text.get_rect(center=(WIDTH//2, 250 + i * 50))
                    if text_rect.collidepoint(mouse_pos):
                        selected_option = i
                        if i == 0 and not signed_in:
                            username = "Player" + str(pygame.time.get_ticks() % 1000)
                            signed_in = True
                        elif i == 1 and signed_in:
                            in_menu = False
                        elif i == 2:
                            running = False
        else:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    in_menu = True
                elif event.key == pygame.K_SPACE:  # Pick up item
                    pick_up_item()
                elif event.key == pygame.K_d:  # Drop item
                    drop_item()


    if not in_menu:
        # Player movement
        keys = pygame.key.get_pressed()
        new_x, new_y = player_x, player_y
       
        if keys[pygame.K_LEFT]:
            new_x -= player_speed
            direction = "left"
            animation_frame += 1
        elif keys[pygame.K_RIGHT]:
            new_x += player_speed
            direction = "right"
            animation_frame += 1
        elif keys[pygame.K_UP]:
            new_y -= player_speed
            direction = "up"
            animation_frame += 1
        elif keys[pygame.K_DOWN]:
            new_y += player_speed
            direction = "down"
            animation_frame += 1
        else:
            animation_frame += 1  # Breathing animation when idle
       
        # Boundary checking
        player_x = max(30, min(new_x, WIDTH - 30))
        player_y = max(30, min(new_y, HEIGHT - 30))
       
        if check_collision():
            player_x = WIDTH // 2
            player_y = HEIGHT // 2


        # Update held item position
        if held_item:
            held_item.rect.x = player_x - 20
            held_item.rect.y = player_y - 40


        # Drawing game
        draw_warehouse()
        draw_player(player_x, player_y, animation_frame)
        draw_inventory()
    else:
        # Drawing menu
        draw_menu()


    pygame.display.flip()
    clock.tick(30)


pygame.quit()
sys.exit()
