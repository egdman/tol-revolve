# External / system
from __future__ import print_function, absolute_import
import random
import sys
import math
import trollius
from trollius import From, Return, Future
import time
import itertools
import csv
import os
from datetime import datetime
from functools import partial

# Pygazebo
from pygazebo.msg import world_control_pb2, poses_stamped_pb2, world_stats_pb2

# Revolve / sdfbuilder
from revolve.angle import Tree
from sdfbuilder.math import Vector3
from sdfbuilder import SDF, Model, Pose, Link

# Local
from revolve.util import multi_future
from revolve.spec.msgs import ModelInserted

from ..config import constants, parser, str_to_address
from ..build import get_builder, get_simulation_robot
from ..spec import get_tree_generator
from ..logging import logger


class LearningManager(WorldManager):

    def __init__(self, conf):
        super(LearningManager, self).__init__(
            world_address=str_to_address(conf.world_address),
            analyzer_address=str_to_address(conf.analyzer_address),
            output_directory=conf.output_directory,
            builder=get_builder(conf),
            pose_update_frequency=conf.pose_update_frequency,
            generator=get_tree_generator(conf),
            restore=conf.restore_directory)


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
    async def create(cls, conf):
        """
        Coroutine to instantiate a Revolve.Angle WorldManager
        :param conf:
        :return:
        """
        self = cls(conf=conf)
        await self._init()
        return self


    def get_world_time(self):
        if self.last_time:
            return self.last_time
        else:
            return 0.0


    async def get_snapshot_data(self):
        data = await super(LearningManager, self).get_snapshot_data()
        data['learners'] = self.learners
        return data


    async def restore_snapshot(self, data):
        await super(LearningManager, self).restore_snapshot(data)
        self.learners = data['learners']

        for learner in self.learners:
            if learner.robot.name not in self.nn_publishers \
            or learner.robot.name not in self.nn_subscribers:
                await self.create_nn_publisher(learner.robot.name)



    def log_info(self, log_name, log_data):
        if self.output_directory and self.path_to_log_dir:
            for filename, data in log_data.items():
                genotype_log_filename = os.path.join(self.path_to_log_dir, log_name, filename)
                with open(genotype_log_filename, "a") as genotype_log_file:
                    genotype_log_file.write(data)



    async def delete_robot(self, robot):
        await super(LearningManager, self).delete_robot(robot)
        # delete .sdf and .pb files when deleting a robot:
        try:
            os.remove(os.path.join(self.output_directory, 'robot_{0}.sdf'.format(robot.robot.id)))
        except OSError:
            pass

        try:
            os.remove(os.path.join(self.output_directory, 'robot_{0}.pb'.format(robot.robot.id)))
        except OSError:
            pass



    async def create_nn_publisher(self, robot_name):
        # initialize publisher for ModifyNeuralNetwork messages:
        modify_nn_publisher = await self.manager.advertise(
                '/gazebo/default/{0}/modify_neural_network'.format(robot_name),
                'gazebo.msgs.ModifyNeuralNetwork')

        # Wait for connections
        await modify_nn_publisher.wait_for_listener()

        def request_done(data):
            resp = Response()
            resp.ParseFromString(data)
            evaluation_result = resp.dbl_data()
            robot_name = resp.response
            fut = self.pending_requests[robot_name]
            fut.set_result(evaluation_result)
            del self.pending_requests[robot_name]


        modify_nn_response_subscriber = self.manager.subscribe(
                topic_name='/gazebo/default/{0}/fitness'.format(robot.name),
                msg_type='gazebo.msgs.Request',
                request_done)

        await modify_nn_response_subscriber.wait_for_connection()
        self.nn_publishers[robot_name] = modify_nn_publisher
        self.nn_subscribers[robot_name] = modify_nn_response_subscriber



    async def run_brain(self, robot_name, brain_msg):
        future = asyncio.Future()
        self.pending_requests[robot_name] = future
        await self.nn_publishers[robot_name].publish(brain_msg)
        return future


    async def add_learner(self, learner, log_name=None, init_brain_list=None):
        # create directory for this learner's logs:
        if log_name is not None and self.path_to_log_dir is not None:
            try:
                os.mkdir(os.path.join(self.path_to_log_dir, log_name))
            except OSError:
                pass

        await self.create_nn_publisher(learner.robot.name)
        # initialize learner with initial list of brains:
        self.learners[learner] = log_name



    async def run(self):
        for learner, log_name in self.learners.items():
            log_callback = None if log_name is None else partial(self.log_info, log_name)
            await learner.run(self, log_callback)
