# External / system
import sys
import math
import asyncio
import time
import csv
import os
from functools import partial

from .config import str_to_address
from .logging import logger
from .gazebo import WorldManager
from .build import get_builder, get_simulation_robot
from .gazebo import RequestHandler


class LearningManager(WorldManager):

    def __init__(self, conf):
        super(LearningManager, self).__init__(
            world_address=str_to_address(conf.world_address),
            analyzer_address=str_to_address(conf.analyzer_address),
            output_directory=conf.output_directory,
            pose_update_frequency=conf.pose_update_frequency,
            restore=conf.restore_directory)

        self.conf = conf

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

        self.learners = []

        # message passing handlers for each robot
        self.robot_handlers = {}


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


    # def get_world_time(self):
    #     if self.last_time:
    #         return self.last_time
    #     else:
    #         return 0.0


    def get_simulation_sdf(self, robot, robot_name):
        """

        :param robot:
        :type robot: PbRobot
        :param robot_name:
        :return:
        :rtype: SDF
        """
        return get_simulation_robot(robot, robot_name, get_builder(self.conf), self.conf)


    def get_snapshot_data(self):
        data = super(LearningManager, self).get_snapshot_data()
        data['learners'] = self.learners
        return data


    async def restore_snapshot(self, data):
        super(LearningManager, self).restore_snapshot(data)
        self.learners = data['learners']

        for _, learner in self.learners:
            if learner.robot.name not in self.robot_handlers:
                await self.create_handler_for_robot(learner.robot.name)



    def log_info(self, log_name, log_data):
        if self.output_directory and self.path_to_log_dir:
            for filename, data in log_data.items():
                genotype_log_filename = os.path.join(self.path_to_log_dir, log_name, filename)
                with open(genotype_log_filename, "a") as genotype_log_file:
                    genotype_log_file.write(data)



    # async def delete_robot(self, robot):
    #     await super(LearningManager, self).delete_robot(robot)
    #     # delete .sdf and .pb files when deleting a robot:
    #     try:
    #         os.remove(os.path.join(self.output_directory, 'robot_{0}.sdf'.format(robot.robot.id)))
    #     except OSError:
    #         pass

    #     try:
    #         os.remove(os.path.join(self.output_directory, 'robot_{0}.pb'.format(robot.robot.id)))
    #     except OSError:
    #         pass


    async def create_handler_for_robot(self, robot_name):
        handler = await RequestHandler.create(
            self.connection,
            request_class = SendNeuralNetwork,
            request_type = "gazebo.msgs.SendNeuralNetwork",
            response_class = EvaluationResult,
            response_type = "gazebo.msgs.EvaluationResult",
            advertise = "/gazebo/default/{0}/modify_neural_network".format(robot_name),
            subscribe = "/gazebo/default/{0}/fitness".format(robot_name),
            id_attr = "id")

        self.robot_handlers[robot_name] = handler



    async def add_learner(self, learner, log_name=None, init_brain_list=None):
        # create directory for this learner's logs:
        if log_name is not None and self.path_to_log_dir is not None:
            try:
                os.mkdir(os.path.join(self.path_to_log_dir, log_name))
            except OSError:
                pass

        await self.create_handler_for_robot(learner.robot.name)
        self.learners.append((log_name, learner))



    async def run_brain(self, robot_name, brain_msg):
        msg = SendNeuralNetwork()
        msg.id = self.get_unique_id()
        msg.neuralNetwork = brain_msg

        handler = self.robot_handlers[robot_name]
        return await handler.do_request(msg)



    async def run(self):
        futures = []
        for log_name, learner in self.learners:
            log_callback = None if log_name is None else partial(self.log_info, log_name)
            future = asyncio.ensure_future(learner.run(self, log_callback))
            futures.append(future)

        still_running = len(futures)
        while still_running > 0:
            await asyncio.sleep(.1) # this line is important
            still_running = sum((1 for f in futures if not f.done()))
