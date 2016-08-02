import logging
import random
import time
import sys
import os, os.path
import importlib
import types

logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

NORTH=0
EAST=1
SOUTH=2
WEST=3

log_direction = ["NORTH", "EAST", "SOUTH", "WEST"]

class Environment(object):
    enemy_location = (-1, -1, -1)
    powerup_location = (-1, -1, -1)
    location = (-1, -1)
    energy = 0
    max_energy = 0
    life = 0
    max_life = 0
    turn = 0
    robot_direction = NORTH
    turret_direction = NORTH
    
    def __init__(self, turn, max_energy, max_life, energy, life, location, enemy_location, powerup_location, robot_direction, turret_direction):
        self.turn = turn
        self.max_energy = max_energy
        self.max_life = max_life
        self.energy = energy
        self.life = life
        self.location = location
        self.enemy_location = enemy_location
        self.powerup_location = powerup_location
        self.robot_direction = robot_direction
        self.turret_direction = turret_direction
        
    def to_dict(self):
        dict = {}
        for attr, value in self:
            dict[attr] = value
        return dict
        
    def __iter__(self):
        for attr in dir(self):
            if attr.startswith("__") or callable(getattr(self, attr)):
                continue
                
            value = getattr(self, attr)
            try:
                if len(value) == 3:
                    yield attr + "_x", value[0]
                    yield attr + "_y", value[1]
                    yield attr + "_age", value[2]
                    continue
                if len(value) == 2:
                    yield attr + "_x", value[0]
                    yield attr + "_y", value[1]
                    continue
            except TypeError:
                pass
            yield attr, value
            
            
class Robot(object):
    name = None
    max_energy = None
    max_life = None
    energy = None
    life = None
    run_function = None
    rf_type = None
    location = (-1, -1)
    enemy_location = (-1, -1, -1)
    powerup_location = (-1, -1, -1)
    robot_direction = NORTH
    turret_direction = NORTH
    environ = None
    turns = None
    playing = False
    path = None

    def __init__(self, name, path, run_function, rf_type="function", reset_function=None, max_energy=100, max_life=100):
        self.name = name
        self.path = path
        self.reset_function = reset_function
        self.run_function = run_function
        self.rf_type = rf_type
        self.max_energy = max_energy
        self.max_life = max_life
        
    def reset(self, size):
        self.turns = 0
        self.playing = True
        self.energy = self.max_energy
        self.life = self.max_life
        self.robot_direction = NORTH
        self.turret_direction = NORTH
        self.size = size
        self.last_command = None
        if self.reset_function is not None:
            self.reset_function()

    def move(self, direction):
        if direction == NORTH:
            if self.location[1] < self.size[1]:
                self.location = (self.location[0], self.location[1] + 1)
            else:
                self.location = (self.location[0], self.size[1])
        elif direction == SOUTH:
            if self.location[1] > 1:
                self.location = (self.location[0], self.location[1] - 1)
            else:
                self.location = (self.location[0], 1)
        elif direction == EAST:
            if self.location[0] < self.size[0]:
                self.location = (self.location[0] + 1, self.location[1])
            else:
                self.location = (self.size[0], self.location[1])        
        elif direction == WEST:
            if self.location[0] > 1:
                self.location = (self.location[0] - 1, self.location[1])
            else:
                self.location = (1, self.location[1])
        logger.debug("%s is facing %s at (%i, %i)" % (self.name, log_direction[self.robot_direction], self.location[0], self.location[1]))

    def forward(self):
        self.move(self.robot_direction)
        
    def backward(self):
        self.move((self.robot_direction + 2) % 4)
        
    def set_location(self, location):
        self.location = location
        
    def update_enemy_location(self, location):
        self.enemy_location = (location[0], location[1], 0)
        
    def update_powerup_location(self, location):
        self.powerup_location = (location[0], location[1], 0)
        
    def check_dead(self):
        if not self.playing:
            return
            
        # If energy is < 0, we're dead
        if self.energy <= 0:
            self.energy = 0
            self.playing = False
            logger.info("%s has run out of energy" % self.name)
            
        # If life is < 0, we're dead
        if self.life <= 0:
            self.life = 0
            self.playing = False
            logger.info("%s has been destroyed" % self.name)
                        
    def cleanup_turn(self):
        if self.enemy_location[2] > -1:
            self.enemy_location = (self.enemy_location[0], self.enemy_location[1], self.enemy_location[2] + 1)
        if self.powerup_location[2] > -1:
            self.powerup_location = (self.powerup_location[0], self.powerup_location[1], self.powerup_location[2] + 1)
        self.energy -= 1
        self.check_dead()

        
    def run_turn(self, turn):
        environ = Environment(turn, self.max_energy, self.max_life,
                              self.energy, self.life, self.location,
                              self.enemy_location, self.powerup_location,
                              self.robot_direction, self.turret_direction)
        if self.rf_type == "function":
            command = self.run_function(**environ.to_dict())
        elif self.rf_type == "class":
            command = self.run_function(environ)
        elif self.rf_type is None:
            command = "w"
        else:
            logger.error("Unknown run function type (rf_type): %s" % self.rf_type)
            raise Error("Unknown run function type (rf_type): %s" % self.rf_type)
        return command
            
    
class World(object):
    turn = 0
    round = 0
    robots = []
    powerups = []
    powerup_count = 0
    size = (-1, -1)
    startfrom_fd = None
    replay_fd = None
    save_fd = None
    game_over = False
    
    def __init__(self, size, startfrom_file, replay_file, save_file, robots, powerups = 1):
        self.size = size
        self.powerup_count = powerups
        self.robots = []
        for i in range(0, len(robots)):
            self.robots.append(robots[i])
        if save_file is not None:
            try:
                self.save_fd = open(save_file, 'w')
            except:
                print "ERROR: Unable to open %s for writing" % save_file
                sys.exit(1)
        if replay_file is not None:
            try:
                self.replay_fd = open(replay_file, 'r')
            except:
                print "ERROR: Unable to open %s for reading.  Does it exist?" % startfrom_file
                sys.exit(1)
            if startfrom_file is not None:
                logger.warning("Unable to both replay and set a starting point, so ignoring starting point file")
                startfrom_file = None
        if startfrom_file is not None:
            try:
                self.startfrom_fd = open(startfrom_file, 'r')
            except:
                print "ERROR: Unable to open %s for reading.  Does it exist?" % startfrom_file
                sys.exit(1)
    
    def get_random_location(self):
        return (random.randint(1, self.size[0]), random.randint(1, self.size[1]))
    
    def next_turn(self):
        self.turn += 1
        self.round = ((self.turn - 1) / len(self.robots)) + 1
        logger.info("Starting turn %i, round %i" % (self.turn, self.round))
        robot = self.robots[self.turn % len(self.robots)]
 
        if robot.playing:
            logger.info("It's %s's turn" % robot.name)
            self.check_nearby_enemies(robot)
            self.check_nearby_powerups(robot)
            exit = False
            try:
                if self.replay_fd is None:
                    command = robot.run_turn(self.round)
                else:
                    command = self.read_command()
                    if command.startswith('cr '):
                        dead_robot_name = command[3:]
                        logger.error("%s has crashed and is now dead!" % dead_robot_name)
                        for r in self.robots:
                            if r.name == dead_robot_name:
                                r.playing = False
                        exit = True
                    if command is None:
                        logger.info("Replay finished")
                        self.game_over = True
                        return robot
                if not exit:
                    if (type(command) == types.ListType or type(command) == types.TupleType):
                        if len(command) > 1:
                            self.check_command(robot, command[0], command[1:])
                        else:
                            self.check_command(robot, command[0], ())
                    else:
                        self.check_command(robot, command, ())
            except:
                self.write('cr %s\n' % robot.name)
                logger.exception("%s has crashed and is now dead!" % robot.name)
                robot.playing = False

        robot.cleanup_turn()
        if not robot.playing:
             logger.info("%s has died" % robot.name)
        
        cr = robot
        
        # Check how many robots are alive and tell them to prepare for next turn
        alive = 0
        for robot in self.robots:
            if not robot.playing:
                continue
            logger.debug("%s has %i life points and %i energy" % (robot.name, robot.life, robot.energy))
            alive += 1
            alive_name = robot.name
            alive_path = robot.path
        
        # Return false if game is over
        if alive < 2:
            if alive == 0:
                print "All robots are now dead"
                print "Game over"
            else:
                if alive_path is None:
                    print "%s has defeated all other robots!" % alive_name
                else:
                    print "%s (%s) has defeated all other robots!" % (alive_name, alive_path)
            self.game_over = True
        
        return cr
        
    def load_new(self):
        # Initialize powerups
        self.powerups = []
        for pu in range(0, self.powerup_count):
            self.powerups.append(self.get_random_location())
            self.write("%i %i\n" % (self.powerups[-1][0], self.powerups[-1][1]))
        self.write("endpu\n")
            
        # Initialize robots
        for robot in self.robots:
            robot.reset(self.size)
            logger.info("Resetting %s" % robot.name)
            robot.set_location(self.get_random_location())
            self.write("%s\n" % (robot.name))
            self.write("%i %i\n" % (robot.location[0], robot.location[1]))
            logger.debug("Putting %s at (%i, %i)" % (robot.name, robot.location[0], robot.location[1]))
        self.write("endrb\n")
        return True
    
    def load(self):
        if self.replay_fd is not None:
            read_fd = self.replay_fd
        elif self.startfrom_fd is not None:
            read_fd = self.startfrom_fd
        else:
            return self.load_new()
        
        self.powerups = []
        data = read_fd.readline()[:-1]
        while data != "endpu":
            try:
                data = data.split(" ", 1)
                self.powerups.append((int(data[0]), int(data[1])))
            except:
                logger.error("Error loading powerups from savegame")
                sys.exit(1)
            self.write("%i %i\n" % (self.powerups[-1][0], self.powerups[-1][1]))
            data = read_fd.readline()[:-1]
        self.write("endpu\n")
        
        if self.replay_fd is not None:
            data = read_fd.readline()[:-1]
            step = 0
            name = None
            robot = None
            while data != "endrb":
                if step == 0:
                    try:
                        name = data.strip()
                    except:
                        logger.error("Error loading robot name from savegame")
                        sys.exit(1)
                    robot = Robot(name, None, None, None, None)
                    self.robots.append(robot)
                    self.write("%s\n" % (name))
                else:
                    try:
                        data = data.split(" ", 1)
                        robot.set_location((int(data[0]), int(data[1])))
                    except:
                        logger.error("Error loading powerups from savegame")
                        sys.exit(1)
                    logger.info("Resetting %s" % robot.name)
                    robot.reset(self.size)
                    self.write("%i %i\n" % (robot.location[0], robot.location[1]))
                    logger.debug("Placing %s at (%i, %i)" % (robot.name, robot.location[0], robot.location[1]))
                data = read_fd.readline()[:-1]
                step = (step + 1) % 2
            self.write("endrb\n")
        else:
            for robot in self.robots:
                robot.reset(self.size)
                logger.info("Resetting %s" % robot.name)
                data = read_fd.readline()[:-1] # Throw away robot name
                data = read_fd.readline()[:-1]
                if data == "endrb":
                    logger.error("Missing robot information in savegame")
                    sys.exit(1)
                try:
                    data = data.split(" ", 1)
                    robot.set_location((int(data[0]), int(data[1])))
                except:
                    logger.error("Error loading robot from savegame")
                    sys.exit(1)
                self.write("%s\n" % (robot.name))
                self.write("%i %i\n" % (robot.location[0], robot.location[1]))
                logger.debug("Placing %s at (%i, %i)" % (robot.name, robot.location[0], robot.location[1]))
                
            data = read_fd.readline()[:-1]
            if data != "endrb":
                logger.error("Missing robot end code")
                sys.exit(1)
            self.write("endrb\n")            
        return True
            
    def read_command(self):
        if self.replay_fd is not None:
            read_fd = self.replay_fd
        elif self.startfrom_fd is not None:
            read_fd = self.startfrom_fd

        data = read_fd.readline()
        if data == "":
            return None
            
        data = data[:-1]
        try:
            command = data.strip()
        except:
            logger.error("Error reading command from savegame")
            sys.exit(1)
        return command
        

    def write(self, data):
        if self.save_fd is not None:
            self.save_fd.write(data)
            
    def start(self):            
        self.load()
        
        # Start running rounds
        self.turn = 0
        return True

    # Check for collisions
    def is_collision(self, robot):
        for check_robot in self.robots:
            if robot == check_robot:
                continue
            if robot.location == check_robot.location:
                logger.info("%s has run into %s" % (robot.name, check_robot.name))
                return True
        return False
        
    def check_nearby_enemies(self, robot):
        if robot.enemy_location[0] >= robot.location[0] - (1 + ((robot.turret_direction == WEST) * 3)) and \
           robot.enemy_location[0] <= robot.location[0] + (1 + ((robot.turret_direction == EAST) * 3)) and \
           robot.enemy_location[1] >= robot.location[1] - (1 + ((robot.turret_direction == SOUTH) * 3)) and \
           robot.enemy_location[1] <= robot.location[1] + (1 + ((robot.turret_direction == NORTH) * 3)):
            robot.enemy_location = (-1, -1, -1)
        for check_robot in self.robots:
            if robot == check_robot:
                continue
            if check_robot.location[0] >= robot.location[0] - (1 + ((robot.turret_direction == WEST) * 3)) and \
               check_robot.location[0] <= robot.location[0] + (1 + ((robot.turret_direction == EAST) * 3)) and \
               check_robot.location[1] >= robot.location[1] - (1 + ((robot.turret_direction == SOUTH) * 3)) and \
               check_robot.location[1] <= robot.location[1] + (1 + ((robot.turret_direction == NORTH) * 3)):
                robot.update_enemy_location(check_robot.location)

    def check_nearby_powerups(self, robot):
        if robot.powerup_location[0] >= robot.location[0] - (1 + ((robot.turret_direction == WEST) * 3)) and \
           robot.powerup_location[0] <= robot.location[0] + (1 + ((robot.turret_direction == EAST) * 3)) and \
           robot.powerup_location[1] >= robot.location[1] - (1 + ((robot.turret_direction == SOUTH) * 3)) and \
           robot.powerup_location[1] <= robot.location[1] + (1 + ((robot.turret_direction == NORTH) * 3)):
            robot.powerup_location = (-1, -1, -1)

        for pu in self.powerups:
            if pu[0] >= robot.location[0] - (1 + ((robot.turret_direction == WEST) * 3)) and \
               pu[0] <= robot.location[0] + (1 + ((robot.turret_direction == EAST) * 3)) and \
               pu[1] >= robot.location[1] - (1 + ((robot.turret_direction == SOUTH) * 3)) and \
               pu[1] <= robot.location[1] + (1 + ((robot.turret_direction == NORTH) * 3)):
                robot.update_powerup_location(pu)

    # Send out EMP (range 2)
    def emp(self, robot):
        for check_robot in self.robots:
            if robot == check_robot:
                continue
            if check_robot.location[0] >= robot.location[0]-2 and \
               check_robot.location[0] <= robot.location[0]+2 and \
               check_robot.location[1] >= robot.location[1]-2 and \
               check_robot.location[1] <= robot.location[1]+2:
                check_robot.life -= 30
                logger.info("%s hit %s with an EMP" % (robot.name, check_robot.name))
                check_robot.check_dead()
                return True
        return False
        
    # Fire laser
    def laser(self, robot):
        for check_robot in self.robots:
            if robot == check_robot:
                continue
            if (robot.turret_direction == NORTH and \
                    check_robot.location[0] == robot.location[0] and \
                    check_robot.location[1] > robot.location[1]) or \
               (robot.turret_direction == SOUTH and \
                    check_robot.location[0] == robot.location[0] and \
                    check_robot.location[1] < robot.location[1]) or \
               (robot.turret_direction == EAST and \
                    check_robot.location[0] > robot.location[0] and \
                    check_robot.location[1] == robot.location[1]) or \
               (robot.turret_direction == WEST and \
                    check_robot.location[0] < robot.location[0] and \
                    check_robot.location[1] == robot.location[1]):
                check_robot.life -= 90
                logger.info("%s hit %s with a laser" % (robot.name, check_robot.name))
                check_robot.check_dead()
                return True
        return False
        
    # Check and claim any powerups
    def check_goodies(self, robot):
        for i in range(0, len(self.powerups)):
            if robot.location == self.powerups[i]:
                robot.energy = 100
                del self.powerups[i]

    def goto_command(self, robot, argument):
        x = argument[0]
        y = argument[1]
        try:
            x = int(x)
            y = int(y)
        except:
            logger.warn("goto %s, %s: coordinates aren't integers" % (argument[0], argument[1]))
            return "w", ()
        if x < 1 or x > self.size[0] or y < 1 or y > self.size[1]:
            logger.warn("goto %i, %i: coordinates aren't within range (1, 1) - (%i, %i)" % (x, y, self.size[0], self.size[1]))
            return "w", ()

        if x == robot.location[0] and y == robot.location[1]:
            logger.warn("goto %i, %i: robot is already at requested coordinates" % (x, y))
            return "w", ()
            
        delta_x = 0
        delta_y = 0
        # Work out x direction we need to go and difference between current direction and target
        if x > robot.location[0]:
            direction_x = 1
            if robot.robot_direction == 1:
                delta_x = 0
            elif robot.robot_direction == 0 or robot.robot_direction == 2:
                delta_x = 1
            else: # direction == 3
                delta_x = 2
        elif x < robot.location[0]:
            direction_x = 3
            if robot.robot_direction == 3:
                delta_x = 0
            elif robot.robot_direction == 0 or robot.robot_direction == 2:
                delta_x = 1
            else: # direction == 1
                delta_x = 2
        else:
            direction_x = -1
            delta_x = 99

        # Work out y direction we need to go and difference between current direction and target
        if y > robot.location[1]:
            direction_y = 0
            if robot.robot_direction == 0:
                delta_y = 0
            elif robot.robot_direction == 1 or robot.robot_direction == 3:
                delta_y = 1
            else: # direction == 2
                delta_y = 2
        elif y < robot.location[1]:
            direction_y = 2
            if robot.robot_direction == 2:
                delta_y = 0
            elif robot.robot_direction == 1 or robot.robot_direction == 3:
                delta_y = 1
            else: # direction == 0
                delta_y = 2
        else:
            direction_y = -1
            delta_y = 99

        # Point robot in optimal direction to keep number of rounds required to turn at minimum
        if direction_x >= 0 and direction_y >= 0:
            if delta_x <= delta_y:
                direction = direction_x
            else: # delta_y > delta_x
                direction = direction_y
        elif direction_x >= 0:
            direction = direction_x
        else: # direction_y >= 0
            direction = direction_y

        # Return new commands
        if robot.robot_direction == direction:
            return "fd", ()
        elif direction == 0:
            return "face", ("north",)
        elif direction == 2:
            return "face", ("south",)  
        elif direction == 1:
            return "face", ("east",)
        else: # direction == 3
            return "face", ("west",)

 
    def check_command(self, robot, command, argument):
        # Go to location
        if command == "goto":
            command, argument = self.goto_command(robot, argument)
    
        # Face north
        if command == "face" and len(argument) > 0 and argument[0] == "north":
            if robot.robot_direction == 1 or robot.robot_direction == 2:
                command = "lt"
            elif robot.robot_direction == 3:
                command = "rt"
            else:
                command = "w"

        # Face south
        elif command == "face" and len(argument) > 0 and argument[0] == "south":
            if robot.robot_direction == 0 or robot.robot_direction == 3:
                command = "lt"
            elif robot.robot_direction == 1:
                command = "rt"
            else:
                command = "w"

        # Face east
        elif command == "face" and len(argument) > 0 and argument[0] == "east":
            if robot.robot_direction == 2 or robot.robot_direction == 3:
                command = "lt"
            elif robot.robot_direction == 0:
                command = "rt"
            else:
                command = "w"

        # Face west
        elif command == "face" and len(argument) > 0 and argument[0] == "west":
            if robot.robot_direction == 0 or robot.robot_direction == 1:
                command = "lt"
            elif robot.robot_direction == 2:
                command = "rt"
            else:
                command = "w"
                
        # Face unknown direction
        elif command == "face":
            if len(argument) > 0:
                try:
                    logger.warn("face: Unable to face unrecognized direction %s" % argument[0])
                except:
                    logger.warn("face: Direction must be a string")
            else:
                logger.warn("face: Robot did not specify a direction to face")
            command = "w"

        robot.last_command = command
        self.write("%s\n" % command)
        
        # Robot is scanning for enemy
        if command == 'se':
            cost = 9
            
            logger.info("%s is scanning for closest enemy" % robot.name)
            if robot.energy > cost:
                robot.energy -= cost
                distance = -1
                location = (-1, -1)
                for check_robot in self.robots:
                    if check_robot == robot:
                        continue
                    if not check_robot.playing:
                        continue
                    check_distance = abs(robot.location[0] - check_robot.location[0]) + abs(robot.location[1] - check_robot.location[1])
                    logger.debug("%s is %i squares away" % (check_robot.name, check_distance))
                    if check_distance < distance or distance == -1:
                        distance = check_distance
                        location = check_robot.location
                logger.info("Closest enemy is at %i, %i" % (location[0], location[1]))
                robot.update_enemy_location(location)
            else:
                robot.last_command = "w"
                logger.warning("%s doesn't have enough energy" % robot.name)
                
        # Robot is scanning for powerups
        elif command == 'sp':
            cost = 9
            
            logger.info("%s is scanning for closest powerup" % robot.name)
            if robot.energy > cost:
                robot.energy -= cost
                distance = -1
                location = (-1, -1)
                for pu in self.powerups:
                    check_distance = abs(robot.location[0] - pu[0]) + abs(robot.location[1] - pu[1])
                    logger.debug("Powerup is %i squares away" % check_distance)
                    if check_distance < distance or distance == -1:
                        distance = check_distance
                        location = pu
                logger.info("Closest powerup is at %i, %i" % (location[0], location[1]))
                robot.update_powerup_location(location)
            else:
                robot.last_command = "w"
                logger.warning("%s doesn't have enough energy" % robot.name)

        # Turn left
        elif command == "lt":
            cost = 1
            
            logger.info("%s is turning left" % robot.name)
            if robot.energy > cost:
                robot.energy -= cost
                robot.robot_direction = (robot.robot_direction - 1) % 4
                robot.turret_direction = (robot.turret_direction - 1) % 4
                logger.debug("%s is now facing %s" % (robot.name, log_direction[robot.robot_direction]))
            else:
                robot.last_command = "w"
                logger.warning("%s doesn't have enough energy" % robot.name)

        # Turn right
        elif command == "rt":
            cost = 1
            
            logger.info("%s is turning right" % robot.name)
            if robot.energy > cost:
                robot.energy -= cost
                robot.robot_direction = (robot.robot_direction + 1) % 4
                robot.turret_direction = (robot.turret_direction + 1) % 4
                logger.debug("%s is now facing %i (%s)" % (robot.name, robot.robot_direction, log_direction[robot.robot_direction]))
            else:
                robot.last_command = "w"
                logger.warning("%s doesn't have enough energy" % robot.name)

        # Go forward
        elif command == "fd":
            cost = 1
            
            logger.info("%s moving forward" % robot.name)
            if robot.energy > cost:
                robot.energy -= cost
                robot.forward()
                if self.is_collision(robot):
                    robot.backward()
                self.check_goodies(robot)
                logger.debug("%s is now at (%i, %i)" % (robot.name, robot.location[0], robot.location[1]))
            else:
                robot.last_command = "w"
                logger.warning("%s doesn't have enough energy" % robot.name)

        # Go backward
        elif command == "bk":
            cost = 4
            
            logger.info("%s moving backward" % robot.name)
            if robot.energy > cost:
                robot.energy -= cost
                robot.backward()
                if self.is_collision(robot):
                    robot.forward()
                self.check_goodies(robot)
                logger.debug("%s is now at (%i, %i)" % (robot.name, robot.location[0], robot.location[1]))
            else:
                logger.warning("%s doesn't have enough energy" % robot.name)
 
        # Fire EMP
        elif command == "emp":
            cost = 4
            
            logger.info("%s fired EMP" % robot.name)
            if robot.energy > cost:
                robot.energy -= cost
                self.emp(robot)
            else:
                robot.last_command = "w"
                logger.warning("%s doesn't have enough energy" % robot.name)
                
        # Fire laser
        elif command == "laser":
            cost = 9
            
            logger.info("%s fired a laser" % robot.name)
            if robot.energy > cost:
                robot.energy -= cost
                self.laser(robot)
            else:
                robot.last_command = "w"
                logger.warning("%s doesn't have enough energy" % robot.name)
        
        # Wait out turn
        elif command == "w":
            logger.info("%s is waiting out this turn" % robot.name)
               
        else:
            logger.warning("%s sent unknown command '%s'" % (robot.name, command))

def usage():
    print "Usage: %s [ --startfrom=savegame ] [ --replay=savegame ] [ --save=savegame ] <first_robot.py> <second_robot.py> .." % sys.argv[0]
    
def load(arguments):
    roblibs = []
    robots = []
    robot_files = []
    startfrom_file = None
    replay_file = None
    save_file = None
    
    for arg in arguments:
        if arg.startswith('--'):
            arglist = arg[2:].split('=', 1)
            if len(arglist) != 2:
                print "You must specify a savegame with --%s" % (arglist[0])
                sys.exit(1)
            if arglist[0] == 'startfrom':
                startfrom_file = arglist[1]
            elif arglist[0] == 'replay':
                replay_file = arglist[1]
            elif arglist[0] == 'save':
                save_file = arglist[1]
            else:
                print "Unrecognized argument %s" % (arg)
                sys.exit(1)
        else:
            robot_files.append(arg)
            
    if replay_file is not None:
        if len(robot_files) != 0:
            print "You must not specify any robots in replay mode"
            usage()
            sys.exit(1)
    else:
        if len(robot_files) != 2:
            print "You must specify two robots"
            usage()
            sys.exit(1)
        
        sys.path.append(os.getcwd())
        for robimpstr in robot_files:
            if robimpstr.endswith('.py'):
                robimpstr = robimpstr[:-3]
            try:
                robimp = importlib.import_module(robimpstr)
            except:
                logger.exception("Unable to import %s" % robimpstr)
                return None
            if not hasattr(robimp, "function_type"):
                robimp.function_type = "function"
            if not hasattr(robimp, "reset"):
                robimp.reset = None
            if not hasattr(robimp, "name"):
                logger.error("%s.py must have the variable 'name' set" % robimpstr)
                return None
            if not hasattr(robimp, "run") or not callable(getattr(robimp, "run")):
                logger.error("%s.py must have a function named 'run()'" % robimpstr)
                return None
            robot = Robot(robimp.name, os.path.basename(robimpstr), robimp.run, robimp.function_type, robimp.reset)
            robots.append(robot)
    
    world = World((16, 9), startfrom_file, replay_file, save_file, robots)
    return world
    
def main():
    world = load(sys.argv[1:])

    if world is None:
        sys.exit(1)
        
    if not world.start():
        sys.exit(1)
        
    while True:
        world.next_turn()
        if world.game_over:
            break

if __name__ == '__main__':
    main()
