import os
import sys
import fnmatch
import csv
import logging
import shutil

from pygazebo.pygazebo import DisconnectError
from trollius.py33_exceptions import ConnectionResetError, ConnectionRefusedError

# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../')

# Trollius / Pygazebo
import trollius
from trollius import From, Return, Future
from pygazebo.msg.request_pb2 import Request

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# Revolve
from revolve.util import multi_future, wait_for
from revolve.convert.yaml import yaml_to_robot
from revolve.angle import Tree

#ToL
from tol.config import parser
from tol.manage import World
from tol.logging import logger, output_console
from tol.spec import get_body_spec, get_brain_spec
from tol.triangle_of_life import RobotLearner
from tol.triangle_of_life.encoding import Mutator, Crossover
from tol.triangle_of_life.convert import yaml_to_genotype


# Log output to console
output_console()
logger.setLevel(logging.DEBUG)

parent_color = (1, 0, 0, 0.5)
child_color = (0, 1, 0, 0.5)

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

parser.add_argument(
    '--eval-time',
    default=15,
    type=float,
    help="time of individual evaluation in simulation seconds"
)

parser.add_argument(
    '--test-bot',
    type=str,
    help="path to file containing robot morphology to test learning on"
)

parser.add_argument(
    '--speciation-threshold',
    type=float,
    default=0.5,
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



class LearningManager(World):
    def __init__(self, conf, _private):
        super(LearningManager, self).__init__(conf, _private)

        self.fitness_filename = None
        self.fitness_file = None
        self.write_fitness = None
        self.learner_list = []
        self.learner_data = []


        self.body_spec = get_body_spec(conf)
        self.brain_spec = get_brain_spec(conf)
        self.mutator = Mutator(self.brain_spec)

        if self.output_directory:
            self.fitness_filename = os.path.join(self.output_directory, 'fitness.csv')

            if self.do_restore:
                shutil.copy(self.fitness_filename + '.snapshot', self.fitness_filename)
                self.fitness_file = open(self.fitness_filename, 'ab', buffering=1)
                self.write_fitness = csv.writer(self.fitness_file, delimiter=',')
            else:
                self.fitness_file = open(self.fitness_filename, 'wb', buffering=1)
                self.write_fitness = csv.writer(self.fitness_file, delimiter=',')
                self.write_fitness.writerow(['t_sim', 'robot_id', 'age', 'displacement',
                                             'vel', 'dvel', 'fitness'])


    @classmethod
    @trollius.coroutine
    def create(cls, conf):
        """
        Coroutine to instantiate a Revolve.Angle WorldManager
        :param conf:
        :return:
        """
        self = cls(_private=cls._PRIVATE, conf=conf)
        yield From(self._init())
        raise Return(self)


    @trollius.coroutine
    def create_snapshot(self):
        """
        Copy the fitness file in the snapshot
        :return:
        """
        ret = yield From(super(LearningManager, self).create_snapshot())
        if not ret:
            raise Return(ret)

        self.fitness_file.flush()
        shutil.copy(self.fitness_filename, self.fitness_filename + '.snapshot')


    @trollius.coroutine
    def get_snapshot_data(self):
        data = yield From(super(LearningManager, self).get_snapshot_data())
        data['learners'] = self.learner_list
        data['innovation_number'] = self.mutator.innovation_number
        raise Return(data)


    def restore_snapshot(self, data):
        yield From(super(LearningManager, self).restore_snapshot(data))
        self.learner_list = data['learners']
        self.mutator.innovation_number = data['innovation_number']


    def add_learner(self, learner):
        self.learner_list.append(learner)


    def log_info(self, log_data):
        if self.output_directory:
            for filename, data in log_data.items():
                genotype_log_filename = os.path.join(self.output_directory, filename)
                genotype_log_file = open(genotype_log_filename, "a")
                genotype_log_file.write(data)
                genotype_log_file.close()


    @trollius.coroutine
    def run(self, conf):

        # brain population size:
        pop_size = conf.population_size
        tournament_size = conf.tournament_size
        evaluation_time = conf.eval_time  # in simulation seconds
        num_children = conf.num_children
        speciation_threshold = conf.speciation_threshold # similarity threshold for fitness sharing

        # after how many generations we stop the experiment:
        max_generations = conf.max_generations


        # # FOR DEBUG
        # ###############################################
        # # brain population size:
        # pop_size = 4
        # tournament_size = 2
        # evaluation_time = 2  # in simulation seconds
        # ###############################################

        yield From(self.pause(True))
        print "### time now is {0}".format(self.last_time)

        if not self.do_restore:

            with open(conf.test_bot,'r') as yamlfile:
                bot_yaml = yamlfile.read()

            pose = Pose(position=Vector3(0, 0, 0))
            bot = yaml_to_robot(self.body_spec, self.brain_spec, bot_yaml)
            tree = Tree.from_body_brain(bot.body, bot.brain, self.body_spec)

            robot = yield From(wait_for(self.insert_robot(tree, pose)))

            print "population size      set to {0}".format(pop_size)
            print "tournament size      set to {0}".format(tournament_size)
            print "number of children   set to {0}".format(num_children)
            print "evaluation time      set to {0}".format(evaluation_time)
            print "speciation threshold set to {0}".format(speciation_threshold)
            print "\nmax number of generations set to {0}".format(max_generations)

            learner = RobotLearner(world=self,
                                       robot=robot,
                                       body_spec=self.body_spec,
                                       brain_spec=self.brain_spec,
                                       mutator=self.mutator,
                                       population_size=pop_size,
                                       tournament_size=tournament_size,
                                       num_children=num_children,
                                       evaluation_time=evaluation_time, # simulation seconds
                                       evaluation_time_sigma=2,         # for eval. time randomization
                                       weight_mutation_probability=0.8,
                                       weight_mutation_sigma=5,
                                       param_mutation_probability=0.8,
                                       param_mutation_sigma=5,
                                       structural_mutation_probability=0.8,
                                       max_num_generations=max_generations,
                                       speciation_threshold=speciation_threshold)


            gen_files = []
            for file_name in os.listdir('./output/restore'):
                if fnmatch.fnmatch(file_name, "gen_*_genotypes.log"):
                    gen_files.append(file_name)


            num_generations = len(gen_files)

            # if we are reading an initial population from a file:
            if num_generations > 0:
                num_brains_evaluated = pop_size*num_generations
                learner.total_brains_evaluated = num_brains_evaluated
                learner.generation_number = num_generations
                # sort genotype files alphanumerically:
                gen_files = sorted(gen_files, key=lambda item: int(item.split('_')[1]))

                last_gen_file = gen_files[-1]
                print "last generation file = {0}".format(last_gen_file)

                init_brain_list, min_mark, max_mark = \
                    get_brains_from_file('./output/restore/' + last_gen_file, self.brain_spec)

                print "Max historical mark = {0}".format(max_mark)

                # set mutator's innovation number according to the max historical mark:
                self.mutator.innovation_number = max_mark + 1

                # initialize learner:
                yield From(learner.initialize(world=self, init_genotypes=init_brain_list))

            # if we don't have a file with an initial population, we generate it ourselves:
            else:
                # initialize learner:
                yield From(learner.initialize(world=self))

            self.add_learner(learner)

        # if the state is being restored:
        else:
            # set new experiment parameters:
            learner = self.learner_list[0]
            learner.population_size = pop_size
            learner.tournament_size = tournament_size
            learner.evaluation_time = evaluation_time
            learner.num_children = num_children
            learner.speciation_threshold = speciation_threshold
            learner.max_generations = max_generations

            print "WORLD RESTORED FROM {0}".format(self.world_snapshot_filename)
            print "STATE RESTORED FROM {0}".format(self.snapshot_filename)

            print "population size      set to {0}".format(learner.population_size)
            print "tournament size      set to {0}".format(learner.tournament_size)
            print "number of children   set to {0}".format(learner.num_children)
            print "evaluation time      set to {0}".format(learner.evaluation_time)
            print "speciation threshold set to {0}".format(learner.speciation_threshold)
            print "\nmax number of generations set to {0}".format(learner.max_generations)

        # Request callback for the subscriber
        def callback(data):
            req = Request()
            req.ParseFromString(data)

        subscriber = self.manager.subscribe(
            '/gazebo/default/request', 'gazebo.msgs.Request', callback)
        yield From(subscriber.wait_for_connection())

        # # sleep for 60 seconds:
        # yield From(self.pause(False))
        # yield From(sleep_sim_time(self, 60))
        # yield From(self.pause(True))

        # run loop:
        while True:
            for learner in self.learner_list:
                result = yield From(learner.update(self, self.log_info))
            if result:
                break


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
    conf.pose_update_frequency = 20

    world = yield From(LearningManager.create(conf))

    print "WORLD CREATED"
    yield From(world.run(conf))


def get_brains_from_file(brain_file_path, brain_spec):
        '''
        generate a population of brains by reading them from file
        :param brain_file:
        :return:
        '''
        brain_list = []
        with open(brain_file_path, 'r') as brain_file:
            yaml_string = ''
            for line in brain_file:
                if 'velocity' in line:
                    if yaml_string != '':
                        brain_list.append(yaml_to_genotype(yaml_string, brain_spec, keep_historical_marks=True))
                        yaml_string = ''
                    continue
                yaml_string += line
            brain_list.append(yaml_to_genotype(yaml_string, brain_spec, keep_historical_marks=True))

        # find min and max historical marks:
        min_mark, max_mark = brain_list[0].min_max_hist_mark()
        for br in brain_list:
            loc_min, loc_max = br.min_max_hist_mark()
            if loc_min < min_mark:
                min_mark = loc_min

            if loc_max > max_mark:
                max_mark = loc_max

        return brain_list, min_mark, max_mark




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
