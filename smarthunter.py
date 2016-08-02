name = "hunterbot"

shots = 0

def run(turn, max_energy, max_life, energy, life,
        robot_direction, turret_direction,
        location_x, location_y,
        enemy_location_x, enemy_location_y, enemy_location_age,
        powerup_location_x, powerup_location_y, powerup_location_age):

    global shots

    if enemy_location_x == -1:
        return "se"

    if shots > 2:
        shots = 0
        return "se"

    if enemy_location_x == location_x:
        if enemy_location_y > location_y:
            if robot_direction != 0:
                return "face", "north"
            else:
                shots += 1
                return "laser"
        if enemy_location_y < location_y:
            if robot_direction != 2:
                return "face", "south"
            else:
                shots += 1
                return "laser"

    if enemy_location_y > location_y or enemy_location_y < location_y:
        return "goto", location_x, enemy_location_y

    if enemy_location_x < location_x:
        if robot_direction != 3:
            return "face", "west"
        else:
            shots += 1
            return "laser"

    if enemy_location_x > location_x:
        if robot_direction != 1:
            return "face", "east"
        else:
            shots +=1
            return "laser"
