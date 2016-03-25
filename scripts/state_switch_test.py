import os
import sys
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from tol.util import StateSwitch

def run():
    cur_time = time.time()
    ssw = StateSwitch(['state1', 'state2', 'state3'], cur_time)

    ssw.set_duration('state2', 3)
    ssw.set_duration('state3', 6)

    cur_state = ssw.get_current_state()
    print cur_state
    while True:
        next_state = ssw.update(time.time())
        if next_state != cur_state:
            cur_state = next_state
            print cur_state


if __name__ == '__main__':
    run()
