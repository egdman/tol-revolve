# import os
# import sys
# import csv
# import logging
# import shutil
#
# from pygazebo.pygazebo import DisconnectError
# from trollius.py33_exceptions import ConnectionResetError, ConnectionRefusedError
#
# # Add "tol" directory to Python path
# sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../')
#
# # Trollius / Pygazebo
# import trollius
# from trollius import From, Return, Future
# from pygazebo.msg.request_pb2 import Request
#
# # sdfbuilder
# from sdfbuilder.math import Vector3
# from sdfbuilder import Pose, Model, Link, SDF
#
# # Revolve
# from revolve.util import multi_future, wait_for
# from revolve.convert.yaml import yaml_to_robot
# from revolve.angle import Tree
# from revolve.build.util import in_grams, in_mm
#
# from sdfbuilder import Link, Model, SDF
# from sdfbuilder.math import Vector3, Quaternion
#
# #ToL
# from tol.config import parser
# from tol.manage import World
# from tol.logging import logger, output_console
# from tol.spec import get_body_spec, get_brain_spec
#
# from tol.learning.convert import NeuralNetworkParser, yaml_to_genotype
# from tol.util import random_rotation, rotate_vertical, Timers


# # Log output to console
# output_console()
# logger.setLevel(logging.DEBUG)


# class SwapTest(World):
#     def __init__(self, conf, _private):
#         super(SwapTest, self).__init__(conf, _private)
#
#         body_files = []
#         for file_name in os.listdir("body"):
#             body_files.append(file_name)
#         self.body_file = body_files[0]
#
#         self.brain_files = []
#         for file_name in os.listdir("brains"):
#             self.brain_files.append(file_name)
#
#         self.body_spec = None
#         self.brain_spec = None
#         self.nn_parser = None
#         self.modify_nn_publisher = None
#         self.robot_name = None
#         self.brain_genotypes = []
#         self.timers = Timers(['evaluate'], 0)
#         self.time_period = 5.0
#
#
#     @trollius.coroutine
#     def run(self, conf):
#         conf.min_parts = 1
#         conf.max_parts = 3
#         conf.arena_size = (3, 3)
#         conf.max_lifetime = 99999
#         conf.initial_age_mu = 99999
#         conf.initial_age_sigma = 1
#         conf.age_cutoff = 99999
#
#         self.body_spec = get_body_spec(conf)
#         self.brain_spec = get_brain_spec(conf)
#         self.nn_parser = NeuralNetworkParser(self.brain_spec)
#
#         print "OPENING FILES!!!!!!!!!!!!!!!!!!!"
#         with open("body/{0}".format(self.body_file),'r') as robot_file:
#             robot_yaml = robot_file.read()
#
#
#
#
#         for filename in self.brain_files:
#             with open("brains/{0}".format(filename, 'r')) as brain_file:
#                 br_yaml = brain_file.read()
#                 self.brain_genotypes.append(yaml_to_genotype(br_yaml, self.brain_spec))
#
#
#
#         yield From(wait_for(self.pause(True)))
#
#
#         pose = Pose(position=Vector3(0, 0, 0.5), rotation=rotate_vertical(0))
#
#         robot_pb = yaml_to_robot(self.body_spec, self.brain_spec, robot_yaml)
#         tree = Tree.from_body_brain(robot_pb.body, robot_pb.brain, self.body_spec)
#
#
#         print "INSERTING ROBOT!!!!!!!!!!!!!!!!!!!!!!"
#         robot = yield From(wait_for(self.insert_robot(tree, pose)))
#         self.robot_name = robot.name
#
#         self.modify_nn_publisher = yield From(
#             self.manager.advertise(
#                 '/gazebo/default/{0}/modify_neural_network'.format(self.robot_name),
#                 'gazebo.msgs.ModifyNeuralNetwork',
#             )
#         )
#         # Wait for connections
#         yield From(self.modify_nn_publisher.wait_for_listener())
#
#
#         brain_num = 0
#         num_of_brains = len(self.brain_genotypes)
#         print "Number of brains = {0}".format(num_of_brains)
#
#         yield From(wait_for(self.pause(False)))
#         while (True):
#             if self.timers.is_it_time('evaluate', self.time_period, self.get_world_time()):
#                 print "Switching brain to #{0}!!!!!!!!!".format(brain_num)
#                 yield From(self.insert_brain(self.brain_genotypes[brain_num % num_of_brains]))
#                 self.timers.reset('evaluate', self.get_world_time())
#                 brain_num += 1
#
#
#
#     def get_world_time(self):
#         if self.last_time:
#             return self.last_time
#         else:
#             return 0.0
#
#
#     @trollius.coroutine
#     def insert_brain(self, brain_genotype):
#         # flush neural network of the robot:
#         msg = self.nn_parser.genotype_to_modify_msg(brain_genotype)
#
#         flush_future = yield From(self.request_handler.do_gazebo_request(
#             "flush_neural_network",
#             data=self.robot_name  # we pass robot name as data so that the flush message
#             # is sent to the correct robot
#         ))
#         yield From(flush_future)
#         yield From(self.modify_nn_publisher.publish(msg))
#
#
#
#
# @trollius.coroutine
# def run(conf):
#     swapTest = yield From(SwapTest.create(conf))
#     yield From(swapTest.run(conf))
#
#
#
#
#
# def main():
#     print "START"
#
#     conf = parser.parse_args()
#     conf.pose_update_frequency = 5
#
#
#     def handler(loop, context):
#         exc = context['exception']
#         if isinstance(exc, DisconnectError) or isinstance(exc, ConnectionResetError):
#             print("Got disconnect / connection reset - shutting down.")
#             sys.exit(1)
#
#         raise context['exception']
#
#     try:
#         loop = trollius.get_event_loop()
#         loop.set_debug(enabled=True)
# #        logging.basicConfig(level=logging.DEBUG)
#         loop.set_exception_handler(handler)
#
#
#         loop.run_until_complete(run(conf))
#         print "FINISH"
#
#     except KeyboardInterrupt:
#         print("Got Ctrl+C, shutting down.")
#     except ConnectionRefusedError:
#         print("Connection refused, are the world and the analyzer loaded?")
#


import os
import sys
import logging

import trollius
from trollius import From


# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../')

from tol.config import parser
from tol.logging import logger, output_console
from tol.manage import World


output_console()
logger.setLevel(logging.DEBUG)


@trollius.coroutine
def run(conf):

    world = yield From(World.create(conf))
    yield From(world.pause(False))
    while True:
        continue


def main():
    print "START"

    conf = parser.parse_args()
    conf.pose_update_frequency = 10
    try:
        loop = trollius.get_event_loop()
        loop.set_debug(enabled=True)
        loop.run_until_complete(run(conf))

        print "FINISH"

    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")


if __name__ == '__main__':
    main()
