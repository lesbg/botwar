name = "squarebot"

def run(turn, max_energy, max_life, energy, life,
        robot_direction, turret_direction,
        location_x, location_y,
        enemy_location_x, enemy_location_y, enemy_location_age,
        powerup_location_x, powerup_location_y, powerup_location_age):
    check_count = 7
    if turn % check_count == 0:
        return "rt"
    elif turn % check_count == 1:
        return "laser"
    else:
        return "fd"
