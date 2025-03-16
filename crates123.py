import pygame as pg
import threading
import random
import time

items = {}
items_lock = threading.Lock()

class GameApp:
    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((950, 600))
        self.init_time = time.time()
        try:
            self.crate_image = pg.image.load("assets/crate.png").convert_alpha()
            self.crate_image = pg.transform.scale(self.crate_image, (20, 20))
            print("Crate image loaded successfully.")
        except FileNotFoundError:
            self.crate_image = pg.Surface((20, 20))
            self.crate_image.fill((139, 69, 19))
            print("Crate image not found, using fallback.")
        with items_lock:
            items["crates"] = [
                (pg.Rect(100, 100, 20, 20), False),
                (pg.Rect(200, 200, 20, 20), False)
            ]
        print("Added test crates at (100,100) and (200,200)")

    def run_game(self):
        running = True
        while running:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False

            current_time = time.time()
            if current_time - self.init_time > 5 and "crates" not in items:
                print("Triggering fallback to spawn crates.")
                with items_lock:
                    items["crates"] = [
                        (pg.Rect(random.randint(50, 900), random.randint(50, 550), 20, 20), False)
                        for _ in range(10)
                    ]
                print("Number of crates added:", len(items["crates"]))

            self.screen.fill((0, 0, 0))
            with items_lock:
                items_copy = {item_name: [(rect, collected) for rect, collected in rect_list] 
                             for item_name, rect_list in items.items()}
            print("Items to draw:", items_copy)
            for item_name, rect_list in items_copy.items():
                image = self.crate_image
                for rect, collected in rect_list:
                    self.screen.blit(image, rect)

            pg.display.flip()
        pg.quit()

if __name__ == "__main__":
    game = GameApp()
    game.run_game()