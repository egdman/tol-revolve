import random
import math
from sdfbuilder.math import Vector3, Quaternion


def random_rotation():
    """
    :return:
    :rtype: Quaternion
    """
    x = random.random()*2.0 - 1.0
    y = random.random()*2.0 - 1.0
    z = random.random()*2.0 - 1.0

    norm = math.sqrt(x*x + y*y + z*z)
    x /= norm
    y /= norm
    z /= norm

    angle = random.random() * 2 * 3.14159
    return Quaternion.from_angle_axis(angle, Vector3(x, y, z))


class Timers:
    """
    This class is useful when you want to do some action every T seconds.

    You create Timers object by passing a list of unique names and current time.

    You call the method is_it_time(name, time_period, current_time) to ask whether 'time_period' seconds
    has passed since the moment you created or reset the 'name' timer.

    You set 'name' timer to current time by calling reset(name, current_time).

    You can also add a new 'name' timer by calling reset with the new 'name'.

    """

    def __init__(self, names, current_time):
        self.timers = {name: current_time for name in names}

    def is_it_time(self, name, time_period, current_time):
        last_time = self.timers[name]

        if last_time is not None:
            elapsed = current_time - last_time
            if elapsed >= time_period:
                return True

        return False


    def reset(self, name, current_time):
        self.timers[name] = current_time


    def get_last_time(self, name):
        return self.timers[name]

