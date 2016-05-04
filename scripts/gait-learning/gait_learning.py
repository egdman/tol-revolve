import os
import sys
import logging
import fnmatch
import shutil

from pygazebo.pygazebo import DisconnectError
from trollius.py33_exceptions import ConnectionResetError, ConnectionRefusedError

# Trollius / Pygazebo
import trollius
from trollius import From, Return, Future
from pygazebo.msg.request_pb2 import Request


from sdfbuilder.math import Vector3
from sdfbuilder import Pose

from revolve.util import wait_for
from revolve.convert.yaml import yaml_to_robot
from revolve.angle import Tree

# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../')

#ToL
from tol.config import parser
from tol.logging import logger, output_console
from tol.learning import LearningManager, RobotLearner, RobotLearnerOnline
from tol.learning.encoding import Mutator, get_default_mutation_spec
from tol.learning import get_brains_from_file
from tol.spec import get_body_spec, get_brain_spec


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

parser.add_argument(
    '--online',
    action='store_true',
    help='when this flag is set, the online gait learning mode is used instead of the offline mode'
)


@trollius.coroutine
def run():

    conf = parser.parse_args()
    conf.evaluation_time_sigma = 2.0
    conf.weight_mutation_probability = 0.8
    conf.weight_mutation_sigma = 5.0
    conf.param_mutation_probability = 0.8
    conf.param_mutation_sigma = 0.25
    conf.structural_mutation_probability = 0.8
    conf.removal_mutation_probability = 0.0

    # this is the world state update frequency in simulation Hz
    conf.pose_update_frequency = 5 # in simulation Hz

    # these are irrelevant parameters but we need to set them anyway,
    # otherwise it won't work
    conf.min_parts = 1
    conf.max_parts = 3
    conf.arena_size = (3, 3)
    conf.max_lifetime = 99999
    conf.initial_age_mu = 99999
    conf.initial_age_sigma = 1
    conf.age_cutoff = 99999

    # create the learning manager
    world = yield From(LearningManager.create(conf))

    path_to_log_dir = os.path.join(world.path_to_log_dir, "learner1")
    body_spec = get_body_spec(conf)
    brain_spec = get_brain_spec(conf)

    mut_spec = get_default_mutation_spec(brain_spec)

    # disallow to add oscillators:
    types_of_new_neurons = filter(lambda item: item != "Oscillator", mut_spec['types'])
    mut_spec['types'] = types_of_new_neurons

    print "New types: {0}".format(mut_spec['types'])

    mutator = Mutator(brain_spec, mutation_spec=mut_spec)



    # if we are not restoring a saved state:
    if not world.do_restore:

        with open(conf.test_bot, 'r') as yamlfile:
            bot_yaml = yamlfile.read()

        pose = Pose(position=Vector3(0, 0, 0.2))
        bot = yaml_to_robot(body_spec, brain_spec, bot_yaml)
        tree = Tree.from_body_brain(bot.body, bot.brain, body_spec)

        robot = yield From(wait_for(world.insert_robot(tree, pose)))

        if conf.online:
            learner = RobotLearnerOnline(world=world,
                                   robot=robot,
                                   insert_position=Vector3(0, 0, 0.2),
                                   body_spec=body_spec,
                                   brain_spec=brain_spec,
                                   mutator=mutator,
                                   conf=conf)
        else:
            learner = RobotLearner(world=world,
                                   robot=robot,
                                   insert_position=Vector3(0, 0, 0.2),
                                   body_spec=body_spec,
                                   brain_spec=brain_spec,
                                   mutator=mutator,
                                   conf=conf)

        gen_files = []
        init_brain_list = None

        if (os.path.isdir(path_to_log_dir)):
            for file_name in os.listdir(path_to_log_dir):
                if fnmatch.fnmatch(file_name, "gen_*_genotypes.log"):
                    gen_files.append(file_name)

        # if we are reading an initial population from a file:
        if len(gen_files) > 0:

            gen_files = sorted(gen_files, key=lambda item: int(item.split('_')[1]))
            last_gen_file = gen_files[-1]

            num_generations = int(last_gen_file.split('_')[1]) + 1
            num_brains_evaluated = conf.population_size * num_generations

            print "last generation file = {0}".format(last_gen_file)

            # get list of brains from the last generation log file:
            init_brain_list, min_mark, max_mark = \
                get_brains_from_file(os.path.join(path_to_log_dir, last_gen_file), brain_spec)

            print "Max historical mark = {0}".format(max_mark)

            # set mutator's innovation number according to the max historical mark:
            mutator.innovation_number = max_mark + 1

            learner.total_brains_evaluated = num_brains_evaluated
            learner.generation_number = num_generations

        # initialize learner with initial list of brains:
        yield From(world.add_learner(learner, "learner1", init_brain_list))
        print learner.parameter_string()

        # log experiment parameter values:
        create_param_log_file(conf, learner.generation_number, os.path.join(path_to_log_dir, "parameters.log"))
        # copy the robot body file:
        shutil.copy(conf.test_bot, path_to_log_dir)

    # if we are restoring a saved state:
    else:
        print "WORLD RESTORED FROM {0}".format(world.world_snapshot_filename)
        print "STATE RESTORED FROM {0}".format(world.snapshot_filename)

    print "WORLD CREATED"
    yield From(world.run())


def create_param_log_file(conf, cur_generation, filename):
    with open(filename, 'a') as log_file:
        log_file.write('generation: {0}\n'.format(cur_generation))
        log_file.write("{0}\n".format(str(conf)))



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
