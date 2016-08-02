name = "energybot"

def run(turn, max_energy, max_life, energy, life,
        robot_direction, turret_direction,
        location_x, location_y,
        enemy_location_x, enemy_location_y, enemy_location_age,
        powerup_location_x, powerup_location_y, powerup_location_age):

    if powerup_location_age == -1:
        return "sp"

    if powerup_location_x == -1:
        return "w"

    if powerup_location_x != location_x or powerup_location_y != location_y:
        return "goto", powerup_location_x, powerup_location_y
