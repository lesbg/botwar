#!/usr/bin/python

import botwar
import pygame
import math
import sys
import logging
import os.path
from pygame.locals import *

NORTH=0
EAST=1
SOUTH=2
WEST=3

direction = ["NORTH", "EAST", "SOUTH", "WEST"]

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

screen = None
clock = None
robot_list = None
world = None
w = None

def set_clock(new_clock):
    global clock
    
    clock = new_clock
    
def check_quit():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)

class WorldAnimation(object):
    robot_sprite_list = []
    world = None
    screen_size = None
    height = None
    width = None
    square = None
    pad_x = None
    pad_y = None
    init = False
    
    def __init__(self, world, powerup_file):
        self.world = world
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.powerup_orig_image = pygame.image.load(os.path.join(self.path, powerup_file))
        
    def scale_images(self):
        self.powerup_image = pygame.transform.smoothscale(self.powerup_orig_image, (self.square, self.square))
        
    def add_robot_sprite(self, robot_sprite):
        self.robot_sprite_list.append(robot_sprite)

    def init_game(self):
        if not self.init:
            pygame.init()
            pygame.display.set_caption("Botwars")
            self.init = True
                    
    def optimum_res(self):
        self.init_game()
        info = pygame.display.Info()
        board_ratio = float(self.world.size[0]+4) / float(self.world.size[1])
        screen_ratio = float(info.current_w) / float(info.current_h)
        logger.debug("Board ratio: %.2f" % board_ratio)
        logger.debug("Screen ratio: %.2f" % screen_ratio)
        if board_ratio > screen_ratio:
            choose_width = int(info.current_w / 1.33)
            choose_height = int(choose_width / board_ratio)
        else:
            choose_height = int(info.current_h / 1.33)
            choose_width = int(choose_height * board_ratio)
        return self.set_res(choose_width, choose_height)
        
    def set_res(self, w, h):
        self.init_game()
        screen = pygame.display.set_mode((w, h), DOUBLEBUF | RESIZABLE)
        self.height = h
        self.width = w
        
        sw = float(w) / float(self.world.size[0])
        sh = float(h) / float(self.world.size[1])
        if sw > sh:
            self.square = int(sh)
        else:
            self.square = int(sw)
        self.pad_x = (w - (self.square * self.world.size[0])) / 2
        self.pad_y = (h - (self.square * self.world.size[1])) / 2
        self.scale_images()
        logger.info("Setting resolution to %ix%i with tile size of %i and padding of (%i, %i)" % (w, h, self.square, self.pad_x, self.pad_y))
        return screen
        
    def board_to_screen(self, x, y):
        loc = (((x - 1) * self.square) + self.pad_x + (self.square/2),
               ((self.world.size[1] - y) * self.square) + self.pad_y + (self.square/2))
        return loc
        
    def draw_scores(self):
        height = self.height / ((len(self.robot_sprite_list)+1) / 2)
        block_size = self.pad_x / 20.0
        font = pygame.font.Font(None, self.pad_x/5)
        count = 0
        # Black out scores area
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, self.pad_x, self.height))
        pygame.draw.rect(screen, (0, 0, 0), (self.width - self.pad_x, 0, self.pad_x, self.height))
        for robot_sprite in self.robot_sprite_list:
            count += 1
            robot = robot_sprite.robot
            text = font.render(robot.name, 1, (255, 255, 255))

            top = (height * ((count-1) / 2)) + int(height*0.1)
            bottom = top + int(height*0.8)
            if count % 2 == 1:
                rotation = -90
                left = int(block_size * 6)
                location = (block_size * 3, top + (height/2))
            else:
                rotation = 90
                left = (self.width - self.pad_x) + int(block_size*2)
                location = (self.width - (block_size * 3), top + (height/2))
            text = pygame.transform.rotate(text, rotation) 
            textpos = text.get_rect()
            if textpos[3] > int(height*0.8):
                ratio = (height*0.8) / float(textpos[3])
                text = pygame.transform.smoothscale(textpos[2] * ratio, textpos[3]*ratio)
                textpos = text.get_rect()
            textpos.center = location
            screen.blit(text, textpos)
            for i in range(0, int(height*0.8)):
                # Show energy bar
                energy_color = (0, float(i)/int(height*0.8)*255, 255)
                if float(robot.energy)/float(robot.max_energy) >= float(i)/int(height*0.8):
                    pygame.draw.line(screen, energy_color, (left, top+int(height*0.8)-i), (left+int(block_size*4)-1, top+int(height*0.8)-i))
                # Show life bar
                life_color = ((height*0.8 - float(i))/int(height*0.8)*255, float(i)/int(height*0.8)*255, 0)
                if float(robot.life)/float(robot.max_life) >= float(i)/int(height*0.8):
                    pygame.draw.line(screen, life_color, (left+int(block_size*8), top+int(height*0.8)-i), (left+int(block_size*12)-1, top+int(height*0.8)-i))

            energy_color = (0, float(robot.energy)/float(robot.max_energy)*255, 255)
            life_color = ((float(robot.max_life) - float(robot.life))/float(robot.max_life)*255, float(robot.life)/float(robot.max_life)*255, 0)
            pygame.draw.rect(screen, energy_color, (left, top, int(block_size*4), int(height*0.8)), 1)
            pygame.draw.rect(screen, life_color, (left+int(block_size*8), top, int(block_size*4), int(height*0.8)), 1) 
        	
    def draw_board(self):
        for i in range(0, self.world.size[0]+1):
            pygame.draw.line(screen, (64, 64, 64), (i*self.square + self.pad_x, self.pad_y), (i*self.square + self.pad_x, self.height-self.pad_y))
        for i in range(0, self.world.size[0]+1):
            pygame.draw.line(screen, (64, 64, 64), (self.pad_x, i*self.square + self.pad_y), (self.width-self.pad_x, i*self.square + self.pad_y))
            
    def draw_sight(self):
        for robot_sprite in self.robot_sprite_list:
            robot = robot_sprite.robot
            y = robot_sprite.current_location[1] - self.square*1.5
            x = robot_sprite.current_location[0] - self.square*1.5
            if robot.turret_direction == EAST or robot.turret_direction == WEST:
                s = pygame.Surface((self.square*6, self.square*3), pygame.SRCALPHA)
                if robot.turret_direction == WEST:
                    x -= self.square * 3
            else:
                s = pygame.Surface((self.square*3, self.square*6), pygame.SRCALPHA)
                if robot.turret_direction == NORTH:
                    y -= self.square * 3
            s.fill((255,255,0,32))
            screen.blit(s, (x, y)) 

    def draw_enemy_circles(self):
        count = 0
        for robot_sprite in self.robot_sprite_list:
            count += 1
            if count % 2 == 0:
                red = 1
                blue = 0
            else:
                red = 0
                blue = 1
            robot = robot_sprite.robot
            if robot.enemy_location[0] == -1:
                continue
            enemy_location = robot_sprite.calc_loc(robot.enemy_location[0:2])
            age_check = 10 - robot.enemy_location[2]
            if age_check < 0:
                age_check = 0
            pygame.draw.circle(screen, (red*64 + (red * (age_check * 19.1)), 0, blue*64 + (blue * (age_check * 19.1))), enemy_location, self.square/2, 2)

    def draw_powerups(self):
        for powerup in self.world.powerups:
            rect = self.powerup_image.get_rect()
            rect.center = self.board_to_screen(powerup[0], powerup[1])
            screen.blit(self.powerup_image, rect)
            
    def animate(self):
        self.draw_sight()
        self.draw_scores()
        self.draw_board()
        self.draw_powerups()
        self.draw_enemy_circles()
        for robot_sprite in self.robot_sprite_list:
            robot_sprite.render()

        
class RobotSprite(object):
    robot = None
    w = None
    
    tank_orig_image = None
    turret_orig_image = None
    
    tank_image = None
    turret_image = None
    
    old_location = None
    old_robot_direction = None
    old_turret_direction = None
    
    current_location = None
    current_robot_direction = None
    current_turret_direction = None
    
    frames = None
    current_frame = None
    
    def __init__(self, tank_image, turret_image, robot, w, frames):
        self.w = w
        self.tank_orig_image = pygame.image.load(os.path.join(self.w.path, tank_image))
        self.turret_orig_image = pygame.image.load(os.path.join(self.w.path, turret_image))
        self.robot = robot
        self.frames = frames
        self.current_location = self.calc_loc(self.robot.location)
        self.current_robot_direction = robot.robot_direction*90
        self.current_turret_direction = robot.turret_direction*90
    
    def scale_images(self):
        self.tank_image = pygame.transform.smoothscale(self.tank_orig_image, (self.w.square, self.w.square))
        self.turret_image = pygame.transform.smoothscale(self.turret_orig_image, (self.w.square, self.w.square))
        
    def calc_loc(self, location):
        loc = (((location[0] - 1) * self.w.square) + self.w.pad_x + (self.w.square/2),
               ((self.w.world.size[1] - location[1]) * self.w.square) + self.w.pad_y + (self.w.square/2))
        return loc
        
    def next_turn(self):
        if self.robot.last_command is None:
            screen.fill((0, 0, 0))
            self.w.animate()
            clock.tick(1)
            return
            
        # Last command was movement
        if self.robot.last_command in ['fd', 'bk']:
            old_location = self.current_location
            new_location = self.calc_loc(self.robot.location)
            deltax = (new_location[0] - old_location[0]) / float(self.frames)
            deltay = (new_location[1] - old_location[1]) / float(self.frames)
            for i in range(1, self.frames):
                screen.fill((0, 0, 0))
                self.current_location = (self.current_location[0] + deltax, self.current_location[1] + deltay)
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            screen.fill((0, 0, 0))
            self.current_location = new_location
            self.w.animate()
            pygame.display.flip()
            clock.tick(self.frames)

        # Last command was turning
        elif self.robot.last_command in ['lt', 'rt']:
            old_robot_direction = self.current_robot_direction
            new_robot_direction = self.robot.robot_direction*90
            if old_robot_direction == 270 and new_robot_direction == 0:
                new_robot_direction = 360
            if old_robot_direction == 0 and new_robot_direction == 270:
                old_robot_direction = 360
            delta_robot_direction = (new_robot_direction - old_robot_direction) / float(self.frames)
            old_turret_direction = self.current_turret_direction
            new_turret_direction = self.robot.turret_direction*90
            if old_turret_direction == 270 and new_turret_direction == 0:
                new_turret_direction = 360
            if old_turret_direction == 0 and new_turret_direction == 270:
                old_turret_direction = 360
            delta_turret_direction = (new_turret_direction - old_turret_direction) / float(self.frames)
            for i in range(1, self.frames):
                screen.fill((0, 0, 0))
                self.current_robot_direction = self.current_robot_direction + delta_robot_direction
                self.current_turret_direction = self.current_turret_direction + delta_turret_direction
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            screen.fill((0, 0, 0))
            if new_turret_direction == 360:
                new_turret_direction = 0
            if new_robot_direction == 360:
                new_robot_direction = 0
            self.current_robot_direction = new_robot_direction
            self.current_turret_direction = new_turret_direction
            self.w.animate()
            pygame.display.flip()
            clock.tick(self.frames)
            
        # Last command was scan for enemies
        elif self.robot.last_command == "se":
            delta_color = 255/(self.frames/2)
            for i in range(1, self.frames/2):
                screen.fill((i*delta_color, 0, i*delta_color))
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            for i in range(1, self.frames/2):
                screen.fill((255-(i*delta_color), 0, 255-(i*delta_color)))
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            screen.fill((0, 0, 0))
            self.w.animate()
            pygame.display.flip()
            clock.tick(self.frames)
            
        # Last command was scan for powerups
        elif self.robot.last_command == "sp":
            delta_color = 255/(self.frames/2)
            for i in range(1, self.frames/2):
                screen.fill((0, i*delta_color, 0))
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            for i in range(1, self.frames/2):
                screen.fill((0, 255-(i*delta_color), 0))
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            screen.fill((0, 0, 0))
            self.w.animate()
            pygame.display.flip()
            clock.tick(self.frames)
            
        elif self.robot.last_command == "emp":
            delta_color = 255/(self.frames/2)
            for i in range(1, self.frames/2):
                screen.fill((0, 0, 0))
                rect = pygame.Rect(0, 0, self.w.square*5, self.w.square*5)
                rect.center = self.current_location
                pygame.draw.rect(screen, (i*delta_color, 0, 0), rect)
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            for i in range(1, self.frames/2):
                screen.fill((0, 0, 0))
                rect = pygame.Rect(0, 0, self.w.square*5, self.w.square*5)
                rect.center = self.current_location
                pygame.draw.rect(screen, (255-(i*delta_color), 0, 0), rect)
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            screen.fill((0, 0, 0))
            self.w.animate()
            pygame.display.flip()
            clock.tick(self.frames)
            
        elif self.robot.last_command == "laser":
            delta_color = 255/(self.frames/2)
            for i in range(1, self.frames/2):
                screen.fill((0, 0, 0))
                if self.robot.turret_direction == NORTH:
                    pygame.draw.line(screen, (255, 0, 0), self.current_location, (self.current_location[0], 0), 3)
                elif self.robot.turret_direction == SOUTH:
                    pygame.draw.line(screen, (255, 0, 0), self.current_location, (self.current_location[0], self.w.height), 3)
                elif self.robot.turret_direction == EAST:
                    pygame.draw.line(screen, (255, 0, 0), self.current_location, (self.w.width, self.current_location[1]), 3)
                elif self.robot.turret_direction == WEST:
                    pygame.draw.line(screen, (255, 0, 0), self.current_location, (0, self.current_location[1]), 3)
                self.w.animate()
                check_quit()
                pygame.display.flip()
                clock.tick(self.frames)
            screen.fill((0, 0, 0))
            self.w.animate()
            pygame.display.flip()
            clock.tick(self.frames)
            
        # Wait
        else:
            screen.fill((0, 0, 0))
            self.w.animate()
            check_quit()
            pygame.display.flip()
            clock.tick(1)
            
        return
        
    def render(self):
        if self.current_location[0] == -1 or self.current_location[1] == -1:
            logger.warning("%s isn't on the board yet, so can't render it" % self.robot.name)
            return

        # Render tank and turret
        tankdir = pygame.transform.rotate(self.tank_image, -self.current_robot_direction)
        turretdir = pygame.transform.rotate(self.turret_image, -self.current_turret_direction)
        rect = tankdir.get_rect()
        rect.center = self.current_location
        screen.blit(tankdir, rect)
        rect = turretdir.get_rect()
        rect.center = self.current_location
        screen.blit(turretdir, rect)        
        
        
def animate(robot):
    screen.fill((0, 0, 0))
    for robot_sprite in robot_list:
        if robot_sprite.robot == robot:
            break
            
    if robot_sprite.robot != robot:
        logger.error("Can't find sprite for robot %s" % (robot.name))
        sys.exit(1)
        
    robot_sprite.next_turn()
    
def init():
    global screen
    global clock
    global robot_list
    global world
    global w
        
    world = botwar.load(sys.argv[1:])
    if world is None:
        sys.exit(1)

    if not world.start():
        sys.exit(1)
        
    robot_list = []
    w = WorldAnimation(world, 'powerup.png')

def main():
    global screen
    global clock
    global robot_list
    global world
    global w
            
    i = 0
    for robot in world.robots:
        robot_sprite = RobotSprite('tank-%i.png' % (i+1), 'turret-%i.png' % (i+1), robot, w, 30)
        robot_sprite.scale_images()
        w.add_robot_sprite(robot_sprite)
        robot_list.append(robot_sprite)
        i = 1 - i
        
    screen.fill((0, 0, 0))
    w.animate()
    while True:
        robot = world.next_turn()
        animate(robot)
        if world.game_over:
            break
    for r in w.robot_sprite_list:
        if r.robot.playing:
            if w.width > w.height:
                size = int(w.height * 0.5)
            else:
                size = int(w.width * 0.5)
            tank_image = pygame.transform.smoothscale(r.tank_orig_image, (size, size))
            turret_image = pygame.transform.smoothscale(r.turret_orig_image, (size, size))
            dir_delta = 90 / r.frames
            for i in xrange(0, r.frames * 8):
                check_quit()
                pygame.draw.rect(screen, (0, 0, 0), (w.width / 20, w.height / 20, w.width * 0.9, w.height * 0.9))
                pygame.draw.rect(screen, (128, 128, 128), (w.width / 20, w.height / 20, w.width * 0.9, w.height * 0.9), 1)
                tankdir = pygame.transform.rotate(tank_image, dir_delta*i)
                turretdir = pygame.transform.rotate(turret_image, dir_delta*i)
                rect = tankdir.get_rect()
                rect.center = (w.width / 2, w.height / 2 - 20)
                screen.blit(tankdir, rect)
                rect = turretdir.get_rect()
                rect.center = (w.width / 2, w.height / 2 - 20)
                screen.blit(turretdir, rect)
                font = pygame.font.Font(None, w.height / 10)
                text = font.render(r.robot.name + " wins!", 1, (255, 255, 255))
                rect = text.get_rect()
                rect.center = (w.width / 2, w.height * 0.8)
                screen.blit(text, rect)
                pygame.display.flip()
                clock.tick(r.frames)
                
if __name__ == "__main__":
    clock = pygame.time.Clock()
    init()
    screen = w.optimum_res()
    main()
