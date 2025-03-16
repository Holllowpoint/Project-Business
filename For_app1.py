import pygame as pg
import sys
import random as ran

class Player:
    def __init__(self, x, y, width, height, speed):
        self.rect = pg.Rect(x, y, width, height)
        self.speed = speed

    def move(self, keys, screen_width, screen_height):
        if keys[pg.K_LEFT] and self.rect.x > 0:
            self.rect.x -= self.speed
        if keys[pg.K_RIGHT] and self.rect.x < screen_width - self.rect.width:
            self.rect.x += self.speed
        if keys[pg.K_UP] and self.rect.y > 0:
            self.rect.y -= self.speed
        if keys[pg.K_DOWN] and self.rect.y < screen_height - self.rect.height:
            self.rect.y += self.speed

    def draw(self, screen):
        pg.draw.rect(screen, (100, 100, 100), self.rect)


class Bullet:
    def __init__(self, x, y, width, height, speed):
        self.rect = pg.Rect(x, y, width, height)
        self.speed = speed

    def update(self):
        self.rect.y -= self.speed

    def draw(self, screen):
        pg.draw.rect(screen, (225, 0, 0), self.rect)


class Enemy:
    def __init__(self, x, y, width, height, speed):
        self.rect = pg.Rect(x, y, width, height)
        self.speed = speed

    def update(self):
        self.rect.y += self.speed

    def draw(self, screen):
        pg.draw.rect(screen, (255, 1, 35), self.rect)


class Game:
    def __init__(self):
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pg.display.set_mode((self.screen_width, self.screen_height))
        pg.display.set_caption("Simple Shooter Game")
        self.clock = pg.time.Clock()
        self.player = Player(self.screen_width // 2 - 20, self.screen_height - 70, 40, 60, 5)
        self.bullets = []
        self.enemies = []
        self.enemy_timer = 0
        self.enemy_spawn_time = 2000

    @staticmethod
    def check_collision(rect1, rect2):
        return rect1.colliderect(rect2)

    def run(self):
        while True:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    sys.exit()
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_SPACE:
                        bullet_x = self.player.rect.x + self.player.rect.width // 2 - 2.5
                        bullet_y = self.player.rect.y
                        self.bullets.append(Bullet(bullet_x, bullet_y, 5, 10, 7))

            keys = pg.key.get_pressed()
            self.player.move(keys, self.screen_width, self.screen_height)

            for bullet in self.bullets[:]:
                bullet.update()
                if bullet.rect.y <= 0:
                    self.bullets.remove(bullet)

            current_time = pg.time.get_ticks()
            if current_time - self.enemy_timer > self.enemy_spawn_time:
                enemy_x = ran.randint(0, self.screen_width - 50)
                enemy_y = -50
                self.enemies.append(Enemy(enemy_x, enemy_y, 50, 50, 1.5))
                self.enemy_timer = current_time

            for enemy in self.enemies[:]:
                enemy.update()
                if enemy.rect.y >= self.screen_height:
                    self.enemies.remove(enemy)

            for bullet in self.bullets[:]:
                for enemy in self.enemies[:]:
                    if self.check_collision(bullet.rect, enemy.rect):
                        self.bullets.remove(bullet)
                        self.enemies.remove(enemy)
                        break

            player_rect = self.player.rect
            for enemy in self.enemies[:]:
                if self.check_collision(player_rect, enemy.rect):
                    pg.font.init()
                    self.screen.fill((255, 0, 0))
                    font = pg.font.Font(None, 74)
                    text = font.render("GAME OVER", True, (0, 0, 0))
                    self.screen.blit(text, (self.screen_width // 2 - text.get_width() // 2, self.screen_height // 2 - text.get_height() // 2))
                    pg.display.flip()
                    pg.time.wait(3000)
                    pg.quit()
                    sys.exit()

            self.screen.fill((0, 0, 0))
            self.player.draw(self.screen)

            for bullet in self.bullets:
                bullet.draw(self.screen)

            for enemy in self.enemies:
                enemy.draw(self.screen)

            pg.display.flip()
            self.clock.tick(60)


if __name__ == "__main__":
    game = Game()
    game.run()
    