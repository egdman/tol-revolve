import os
import csv
import logging
import shutil

# Trollius / Pygazebo
import trollius
from trollius import From, Return, Future
from pygazebo.msg.request_pb2 import Request
from pygazebo.msg.response_pb2 import Response
from pygazebo.msg.vector3d_pb2 import Vector3d

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose

# Revolve
from revolve.util import wait_for
from revolve.convert.yaml import yaml_to_robot
from revolve.angle import Tree
from revolve.gazebo import MessagePublisher

#ToL
from ..manage import World
from ..logging import logger, output_console



class LearningManager(World):
    def __init__(self, conf, _private):
        super(LearningManager, self).__init__(conf, _private)

        self.fitness_filename = None
        self.fitness_file = None
        self.write_fitness = None

        self.learners = {}

        # path to the logging directory
        self.path_to_log_dir = None


        # create path to logging directory if directory names are given:
        if conf.output_directory and conf.log_directory:
            # path to the logging directory
            self.path_to_log_dir = os.path.join(conf.output_directory, conf.log_directory)

            # create logging directory:
            try:
                os.mkdir(self.path_to_log_dir)
            except OSError: 
                logger.debug("Directory " + self.path_to_log_dir + " already exists.")


        self.pending_requests = {}

        # publishers that send ModifyNeuralNetwork messages:
        self.nn_publishers = {}

        # subscribers that listen to responses about successful neural network modifications:
        self.nn_subscribers = {}

        # publisher that sends drive_direction_update messages
        self.drive_publisher = None

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


    @trollius.coroutine
    def set_drive_direction(self, x, y, z):
        '''
        publish message containing Vector3d.proto object
        '''
        msg = Vector3d(x=x, y=y, z=z)

        if self.drive_publisher is None:
            # create publisher for the drive direction updates
            self.drive_publisher = yield From(MessagePublisher.create(
                self.manager,
                '/gazebo/default/revolve/drive_direction_update',
                'gazebo.msgs.Vector3d'))

        yield From(self.drive_publisher.publish(msg))


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
        data['learners'] = self.learners
        raise Return(data)


    def restore_snapshot(self, data):
        yield From(super(LearningManager, self).restore_snapshot(data))
        self.learners = data['learners']

        for learner in self.learners:
            if learner.robot.name not in self.nn_publishers or \
                learner.robot.name not in self.nn_subscribers:
                yield From(self.create_nn_publisher(learner.robot.name))


    def log_info(self, log_data, log_name):
        if self.output_directory and self.path_to_log_dir:
            for filename, data in log_data.items():
                genotype_log_filename = os.path.join(self.path_to_log_dir, log_name, filename)
                with open(genotype_log_filename, "a") as genotype_log_file:
                    genotype_log_file.write(data)


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
        modify_nn_publisher = yield From(
            self.manager.advertise(
                '/gazebo/default/{0}/modify_neural_network'.format(robot_name),
                'gazebo.msgs.ModifyNeuralNetwork'
            )
        )
        # Wait for connections
        yield From(modify_nn_publisher.wait_for_listener())

        def request_done(data):
            resp = Response()
            resp.ParseFromString(data)
            robot_name = resp.response
            fut = self.pending_requests[robot_name]
            fut.set_result(robot_name)
            del self.pending_requests[robot_name]

        modify_nn_response_subscriber = self.manager.subscribe(
            '/gazebo/default/{0}/modify_neural_network_response'.format(robot_name), 'gazebo.msgs.Response',
            request_done
        )
        yield From(modify_nn_response_subscriber.wait_for_connection())
        self.nn_publishers[robot_name] = modify_nn_publisher
        self.nn_subscribers[robot_name] = modify_nn_response_subscriber


    @trollius.coroutine
    def modify_brain(self, msg, robot_name):
        fut = Future()
        self.pending_requests[robot_name] = fut
        pub = self.nn_publishers[robot_name]
        yield From(pub.publish(msg))
        raise Return(fut)


    def is_request_satisfied(self, robot_name):
        if robot_name in self.pending_requests:
            return False
        else:
            return True


    @trollius.coroutine
    def add_learner(self, learner, log_name=None, init_brain_list=None):
        # create directory for this learner's logs:
        if log_name is not None and self.path_to_log_dir is not None:
            try:
                os.mkdir(os.path.join(self.path_to_log_dir, log_name))
            except OSError:
                pass

        yield From(self.create_nn_publisher(learner.robot.name))
        # initialize learner with initial list of brains:
        yield From(learner.initialize(world=self, init_genotypes=init_brain_list))
        self.learners[learner] = log_name


    @trollius.coroutine
    def run(self):
        # run loop:
        while True:

            for learner, log_name in self.learners.items():
                if log_name is not None:
                    log_callback = lambda log_data, log_name=log_name: self.log_info(log_data, log_name)
                else:
                    log_callback = None
                result = yield From(learner.update(self, log_callback))
                # if learning is over:
                if result:
                    del self.learners[learner]

            # if there are no learners left, stop the loop
            if len(self.learners) == 0: break

            # this line is important!
            yield From(trollius.sleep(0.1))