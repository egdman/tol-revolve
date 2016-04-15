import os
import fnmatch
import csv
import logging
import shutil

# Trollius / Pygazebo
import trollius
from trollius import From, Return, Future
from pygazebo.msg.request_pb2 import Request
from pygazebo.msg.response_pb2 import Response

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose

# Revolve
from revolve.util import wait_for
from revolve.convert.yaml import yaml_to_robot
from revolve.angle import Tree

#ToL
from ..config import parser
from ..manage import World
from ..logging import logger, output_console
from ..spec import get_body_spec, get_brain_spec

from .robot_learner import RobotLearner, RobotLearnerHotSwap
from .encoding import Mutator
from .convert import yaml_to_genotype
from .utils import get_brains_from_file


class LearningManager(World):
    def __init__(self, conf, _private):
        super(LearningManager, self).__init__(conf, _private)

        self.fitness_filename = None
        self.fitness_file = None
        self.write_fitness = None

        self.learner = None
        self.robot_name = None
        self.pending_requests = {}

        # path to the logging directory
        self.path_to_log_dir = conf.output_directory + "/" + conf.log_directory + "/"

        # publisher that sends ModifyNeuralNetwork messages:
        # It will be initialized after we insert the robot
        self.modify_nn_publisher = None

        # subscriber that listens to responses about successful neural network modifications:
        self.modify_nn_response_subscriber = None

        try:
            os.mkdir(self.path_to_log_dir)
        except OSError:
            print "Directory " + self.path_to_log_dir + " already exists."

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


    def get_world_time(self):
        if self.last_time:
            return self.last_time
        else:
            return 0.0


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
        data['learner'] = self.learner
        data['innovation_number'] = self.mutator.innovation_number
        data['robot_name'] = self.robot_name
        raise Return(data)


    def restore_snapshot(self, data):
        yield From(super(LearningManager, self).restore_snapshot(data))
        self.learner = data['learner']
        self.mutator.innovation_number = data['innovation_number']
        self.robot_name = data['robot_name']
        if self.modify_nn_publisher is None:
            yield From(self.create_nn_publisher(self.robot_name))


    def log_info(self, log_data):
        if self.output_directory:
            for filename, data in log_data.items():
                genotype_log_filename = os.path.join(self.path_to_log_dir, filename)
                genotype_log_file = open(genotype_log_filename, "a")
                genotype_log_file.write(data)
                genotype_log_file.close()



    @trollius.coroutine
    def delete_robot(self, robot):
        yield From(super(LearningManager, self).delete_robot(robot))
        # delete .sdf and .pb files when deleting a robot:
        try:
            os.remove(os.path.join(self.output_directory, 'robot_{0}.sdf'.format(robot.robot.id)))
        except OSError:
            pass

        try:
            os.remove(os.path.join(self.output_directory, 'robot_{0}.pb'.format(robot.robot.id)))
        except OSError:
            pass


    @trollius.coroutine
    def create_nn_publisher(self, robot_name):
        # initialize publisher for ModifyNeuralNetwork messages:
        self.modify_nn_publisher = yield From(
            self.manager.advertise(
                '/gazebo/default/{0}/modify_neural_network'.format(robot_name),
                'gazebo.msgs.ModifyNeuralNetwork'
            )
        )
        # Wait for connections
        yield From(self.modify_nn_publisher.wait_for_listener())

        def request_done(data):
            resp = Response()
            resp.ParseFromString(data)
            robot_name = resp.response
            fut = self.pending_requests[robot_name]
            fut.set_result(robot_name)

            print "CALLBACK {0}".format(robot_name)
            del self.pending_requests[robot_name]

        self.modify_nn_response_subscriber = self.manager.subscribe(
            '/gazebo/default/{0}/modify_neural_network_response'.format(robot_name), 'gazebo.msgs.Response',
            request_done
        )
        yield From(self.modify_nn_response_subscriber.wait_for_connection())



    @trollius.coroutine
    def modify_brain(self, msg, robot_name):
        fut = Future()
        self.pending_requests[robot_name] = fut
        yield From(self.modify_nn_publisher.publish(msg))
        raise Return(fut)


    def is_request_satisfied(self, robot_name):
        if robot_name in self.pending_requests:
            return False
        else:
            return True


    @trollius.coroutine
    def run(self, conf):

        yield From(wait_for(self.pause(True)))

        # if we are starting a new experiment (not restoring from a snapshot)
        if not self.do_restore:

            with open(conf.test_bot,'r') as yamlfile:
                bot_yaml = yamlfile.read()


            pose = Pose(position=Vector3(0, 0, 0.2))
            bot = yaml_to_robot(self.body_spec, self.brain_spec, bot_yaml)
            tree = Tree.from_body_brain(bot.body, bot.brain, self.body_spec)

            robot = yield From(wait_for(self.insert_robot(tree, pose)))

            self.robot_name = robot.name
            print "Robot name is: {0}".format(self.robot_name)


            # create a publisher that will send ModifyNeuralNetwork messages:
            yield From(self.create_nn_publisher(self.robot_name))

            learner = RobotLearnerHotSwap(world=self,
                                       robot=robot,
                                       body_spec=self.body_spec,
                                       brain_spec=self.brain_spec,
                                       mutator=self.mutator,
                                       conf=conf)

            gen_files = []
            for file_name in os.listdir(self.path_to_log_dir):
                if fnmatch.fnmatch(file_name, "gen_*_genotypes.log"):
                    gen_files.append(file_name)

            # if we are reading an initial population from a file:
            if len(gen_files) > 0:

                gen_files = sorted(gen_files, key=lambda item: int(item.split('_')[1]))
                last_gen_file = gen_files[-1]

                num_generations = int(last_gen_file.split('_')[1]) + 1
                num_brains_evaluated = conf.population_size*num_generations

                print "last generation file = {0}".format(last_gen_file)

                # get list of brains from the last generation log file:
                init_brain_list, min_mark, max_mark = \
                    get_brains_from_file(self.path_to_log_dir + last_gen_file, self.brain_spec)

                print "Max historical mark = {0}".format(max_mark)

                # set mutator's innovation number according to the max historical mark:
                self.mutator.innovation_number = max_mark + 1

                learner.total_brains_evaluated = num_brains_evaluated
                learner.generation_number = num_generations

                # initialize learner with initial list of brains:
                yield From(learner.initialize(world=self, init_genotypes=init_brain_list))

            # if we are not reading initial population from file, we generate it:
            else:
                # initialize learner without initial list of brains:
                yield From(learner.initialize(world=self))


            learner.print_parameters()
            self.learner = learner

        # if we are restoring the state from a snapshot
        else:
            # set new experiment parameters:
            learner = self.learner
            learner.set_parameters(conf)
            learner.print_parameters()

            print "WORLD RESTORED FROM {0}".format(self.world_snapshot_filename)
            print "STATE RESTORED FROM {0}".format(self.snapshot_filename)

        # run loop:
        while True:
            result = yield From(self.learner.update(self, self.log_info))
            if result:
                break

            yield From(trollius.sleep(0.2))
