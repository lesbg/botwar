name = "testbot"

def run(turn, max_energy, max_life, energy, life,
        robot_direction, turret_direction,
        location_x, location_y,
        enemy_location_x, enemy_location_y, enemy_location_age,
        powerup_location_x, powerup_location_y, powerup_location_age):
    check_count = 6
    print "%i %i %i %i %i m(%i, %i) e(%i, %i - %i) p(%i, %i - %i)" % \
          (turn, robot_direction, turret_direction, energy, life,
           location_x, location_y,
           enemy_location_x, enemy_location_y, enemy_location_age,
           powerup_location_x, powerup_location_y, powerup_location_age)
    if turn % check_count == 0:
        return "se"
    if turn % check_count == 1:
        return "sp"
    if turn % check_count == 2:
        return "rt"
    if turn % check_count == 3:
        return "fd"
    if turn % check_count == 4:
        return "lt"
    if turn % check_count == 5:
        return "bk"

