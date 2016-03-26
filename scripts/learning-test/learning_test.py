import os
import sys
import logging

from pygazebo.pygazebo import DisconnectError
from trollius.py33_exceptions import ConnectionResetError, ConnectionRefusedError

# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../')

# Trollius / Pygazebo
import trollius
from trollius import From, Return, Future
from pygazebo.msg.request_pb2 import Request

# Revolve
from revolve.build.util import in_grams, in_mm

# ToL
from tol.config import parser
from tol.logging import logger, output_console
from tol.learning import LearningManager


# Log output to console
output_console()
logger.setLevel(logging.DEBUG)

parent_color = (1, 0, 0, 0.5)
child_color = (0, 1, 0, 0.5)

parser.add_argument(
    "--log-directory",
    type=str,
    default="log",
    help="directory where experiment logs are stored"
)

parser.add_argument(
    '--population-size',
    default=10,
    type=int,
    help="number of individuals in brain population"
)

parser.add_argument(
    '--tournament-size',
    default=6,
    type=int,
    help="number of individuals in the tournaments"
)

parser.add_argument(
    '--num-children',
    default=5,
    type=int,
    help="number of children born at each generation;"
    "the new generation will consist of this many children and the rest will be filled with the best of parents"
)

# parser.add_argument(
#     '--evaluation-time',
#     default=15,
#     type=float,
#     help="time of individual evaluation in simulation seconds"
# )

parser.add_argument(
    '--test-bot',
    type=str,
    help="path to file containing robot morphology to test learning on"
)

parser.add_argument(
    '--speciation-threshold',
    type=float,
    default=0.0,
    help="similarity threshold for separating genotypes into different species;"
    "must be between 0 and 1; the smaller it is, the more similar genotypes have to be"
    "to be considered the same species"
)


parser.add_argument(
    '--max-generations',
    type=int,
    help='number of generations in the experiment'
         'the experiment stops when it reaches this number of generations'
)

parser.add_argument(
    '--repeat-evaluations',
    type=int,
    default=1,
    help='number of evaluations per brain'
)


@trollius.coroutine
def run():
    conf = parser.parse_args()
    conf.min_parts = 1
    conf.max_parts = 3
    conf.arena_size = (3, 3)
    conf.max_lifetime = 99999
    conf.initial_age_mu = 99999
    conf.initial_age_sigma = 1
    conf.age_cutoff = 99999
    conf.pose_update_frequency = 5 # in simulation Hz

    world = yield From(LearningManager.create(conf))

    # # insert sound dummy:
    # model_name = yield From(insert_dummy(position=Vector3(20, 0, in_mm(25))))
    #
    # # register dummy as a sound source:
    # yield From(world.attach_sound_source(name=model_name, frequency=frequency))
    #
    # # set sound plugin update frequency:
    # yield From(world.set_sound_update_frequency(update_frequency=2.0))


    print "WORLD CREATED"
    yield From(world.run(conf))



def main():
    print "START"

    def handler(loop, context):
        exc = context['exception']
        if isinstance(exc, DisconnectError) or isinstance(exc, ConnectionResetError):
            print("Got disconnect / connection reset - shutting down.")
            sys.exit(1)

        raise context['exception']

    try:
        loop = trollius.get_event_loop()
        loop.set_debug(enabled=True)
#        logging.basicConfig(level=logging.DEBUG)
        loop.set_exception_handler(handler)
        loop.run_until_complete(run())
        print "EXPERIMENT FINISHED"

    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")
    except ConnectionRefusedError:
        print("Connection refused, are the world and the analyzer loaded?")

if __name__ == '__main__':
    main()
