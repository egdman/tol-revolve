import random
import os
import sys
import logging
import argparse
import math

from revolve.build.util import in_cm, in_mm
from revolve.util import Time

from pygazebo.pygazebo import DisconnectError
from trollius.py33_exceptions import ConnectionResetError, ConnectionRefusedError

# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../')

# Trollius / Pygazebo
import trollius
from trollius import From, Return, Future
from pygazebo.msg.request_pb2 import Request

# # Revolve / sdfbuilder
# from sdfbuilder.math import Vector3
# from sdfbuilder import Pose, Model, Link, SDF

# ToL
from tol.config import parser
# from tol.manage import World
from tol.logging import logger, output_console
# from revolve.util import multi_future
from tol.triangle_of_life import Food_Grid, RobotAccount, EvolutionManager

# Log output to console
output_console()
logger.setLevel(logging.DEBUG)


parser.add_argument("-n", "--num-initial-bots", default=3,
                    help="Number of initial bots", type=int)

# parser.add_argument("-f", "--fast", help="Short reproduction wait.",
#                     action="store_true")


parser.add_argument(
    '--robot-file',
    type=str,
    help="path to file containing robot morphology description in YAML format"
)

parser.add_argument(
    '--brain-genotype-file',
    type=str,
    default=None,
    help="path to file containing brain genotype description in YAML format"
)


parent_color = (1, 0, 0, 0.5)
child_color = (0, 1, 0, 0.5)


# initial food density
init_food_density = 200


#time before robots die
init_life_time = 20

#bonus life time per food item
time_per_food = 10

# maximum mating distance:
mating_distance = 200


@trollius.coroutine
def sleep_sim_time(world, seconds, state_break=[False]):
    """
    Sleeps for a certain number of simulation seconds,
    note that this is always approximate as it relies
    on real world sleeping.
    :param world:
    :param seconds:
    :param state_break: List containing one boolean, the
                        wait will be terminated if this
                        is set to True (basically a hack
                        to break out of automatic mode early).
    :return:
    """
    start = world.last_time if world.last_time else Time()
    remain = seconds

    while remain > 0 and not state_break[0]:
        yield From(trollius.sleep(0.1))
        now = world.last_time if world.last_time else Time()
        remain = seconds - float(now - start)



@trollius.coroutine
def run_server(conf):
    """

    :param args:
    :return:
    """
 #   conf.proposal_threshold = 0
 #   conf.output_directory = None
    conf.min_parts = 1
    conf.max_parts = 2000
    conf.max_inputs = 2000
    conf.max_outputs = 2000

    conf.arena_size = (3, 3)
    conf.max_lifetime = 99999
    conf.initial_age_mu = 99999
    conf.initial_age_sigma = 1
    conf.age_cutoff = 99999

    conf.pose_update_frequency = 5

    conf.init_life_time = init_life_time
    conf.mating_distance = mating_distance
    conf.time_per_food = time_per_food
    conf.init_food_density = init_food_density

    print "WORLD CREATED"

    # # robot accounts:
    # accounts = Population(init_life_time = init_life_time, food_field = food_field,
    #                       mating_distance = mating_distance, time_per_food = time_per_food,
    #                       world = world)


    # initialize world:
    world = yield From(EvolutionManager.create(conf))
    yield From(world.pause(True))


    # Request callback for the subscriber
    def callback(data):
        req = Request()
        req.ParseFromString(data)


    subscriber = world.manager.subscribe(
        '/gazebo/default/request', 'gazebo.msgs.Request', callback)
    yield From(subscriber.wait_for_connection())


    # open files with body and brain descriptions:
    with open(conf.robot_file,'r') as robot_file:
        bot_yaml = robot_file.read()

    brain_genotype_yaml = None

    # if brain genotype file exists:
    if conf.brain_genotype_file != '':
        with open (conf.brain_genotype_file, 'r') as gen_file:
            brain_genotype_yaml = gen_file.read()


    # spawn initial population of robots:
    yield From(world.spawn_initial_given_robots(conf, conf.num_initial_bots, bot_yaml, brain_genotype_yaml))

    yield From(world.pause(False))
    print "WORLD UNPAUSED"

    deltaT = 0.01

    # run loop:
    while True:
        # detect food acquisition:
        for account in world:
            yield From(account.update())


        # reproduce:
        parents = world.find_mate_pairs()
        yield From(world.reproduce(parents))

        # remove dead robots:
        yield From(world.cleanup())

        yield From(trollius.sleep(deltaT))



def main():

    print "START"

    args = parser.parse_args()

    def handler(loop, context):
        exc = context['exception']
        if isinstance(exc, DisconnectError) or isinstance(exc, ConnectionResetError):
            print("Got disconnect / connection reset - shutting down.")
            sys.exit(0)

        raise context['exception']



    try:

        loop = trollius.get_event_loop()

        loop.set_debug(enabled=True)
#        logging.basicConfig(level=logging.DEBUG)

        loop.set_exception_handler(handler)
        loop.run_until_complete(run_server(args))

        # run = run_server(args)
        # run.next()
        # while True:
        #     run.next()

        print "FINISH"

    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")
    except ConnectionRefusedError:
        print("Connection refused, are the world and the analyzer loaded?")

if __name__ == '__main__':
    main()
