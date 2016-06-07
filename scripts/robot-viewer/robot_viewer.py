import os
import sys
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
from revolve.build.util import in_grams, in_mm

from sdfbuilder import Link, Model, SDF
from sdfbuilder.math import Vector3, Quaternion

#ToL
from tol.config import parser
# from tol.manage import World
from tol.logging import logger, output_console
from tol.spec import get_body_spec, get_extended_brain_spec

from tol.learning.convert import NeuralNetworkParser, yaml_to_genotype

from tol.learning import LearningManager as World

from tol.util import random_rotation, rotate_vertical


# Log output to console
output_console()
logger.setLevel(logging.DEBUG)


parser.add_argument(
    '--body-file',
    type=str,
    help="path to YAML file containing robot morphology"
)

parser.add_argument(
    '--brain-file',
    type=str,
    default='',
    help="path to YAML file containing brain genotype"
)

parser.add_argument(
    '--trajectory-file',
    type=str,
    default='',
    help="path to a file for recording the robot's trajectory"

)

parser.add_argument(
    '--trajectory-limit',
    type=float,
    default=0,
    help="how long to record the robot's trajectory (in simulation seconds)"
)

parser.add_argument(
    "--log-directory",
    type=str,
    default="log",
    help="directory where experiment logs are stored"
)

parser.add_argument(
    '--online',
    action='store_true',
    help='when this flag is set, online brain upload is used'
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
    conf.pose_update_frequency = 5

    body_spec = get_body_spec(conf)
    brain_spec = get_extended_brain_spec(conf)


    if conf.trajectory_file != '':
        with open(conf.trajectory_file, 'w+') as out_file:
            out_file.write("{0},{1},{2},{3}\n".format("time", "x", "y", "z"))



    print "OPENING FILES!!!!!!!!!!!!!!!!!!!"
    with open(conf.body_file,'r') as robot_file:
        bot_yaml = robot_file.read()

    genotype_yaml = None

    # if brain genotype file exists:
    if conf.brain_file != '':
        with open (conf.brain_file, 'r') as gen_file:
            genotype_yaml = gen_file.read()

    print "CREATING WORLD!!!!!!!!!!!!!!!!!!!"
    world = yield From(World.create(conf))
    yield From(world.pause(True))

#    pose = Pose(position=Vector3(0, 0, 0.5), rotation=random_rotation())
    pose = Pose(position=Vector3(0, 0, 0.5), rotation=rotate_vertical(0))

    # convert YAML stream to protobuf robot:
    robot_pb = yaml_to_robot(body_spec, brain_spec, bot_yaml)
    body_pb = robot_pb.body
 
    nn_parser = NeuralNetworkParser(brain_spec)

    # if brain genotype is given, combine body and brain:
    if genotype_yaml:

        # convert YAML stream to genotype:
        brain_genotype = yaml_to_genotype(genotype_yaml, brain_spec)

        if conf.online:
            brain_pb = robot_pb.brain
            # brain_pb = nn_parser.genotype_to_brain(brain_genotype)
        else: 
            # convert genotype to protobuf brain:   
            brain_pb = nn_parser.genotype_to_brain(brain_genotype)

    # if brain genotype is not given, get brain from body:
    else:
        brain_pb = robot_pb.brain


    print "INSERTING ROBOT!!!!!!!!!!!!!!!!!!!!!!"

    tree = Tree.from_body_brain(body_pb, brain_pb, body_spec)
    robot = yield From(wait_for(world.insert_robot(tree, pose)))


    yield From(world.pause(False))

    if conf.online:

        # yield From(trollius.sleep(10.0))

        print "UPLOADING BRAIN!!!!!!!!!!!!!!!!!!!!"
        yield From(world.create_nn_publisher(robot.name))

        brain_msg = nn_parser.genotype_to_modify_msg(brain_genotype)
        fut = yield From(world.modify_brain(brain_msg, robot.name))
        yield From(fut)
        print "BRAIN UPLOADED!!!!!!!!!!!!!!!!!!!!!!!!!"


#     print "INSERTING SOUND OBJECTS!!!!!!!!"
#     sound_src_link = Link("sound_src_1_link")
# #    sound_src_link.make_cylinder(mass=in_grams(100), radius=in_mm(50), length=in_mm(20))
#     sound_src_link.make_box(in_grams(100), in_mm(50), in_mm(50), in_mm(50))
#
#     sound_src_model = Model("sound_src_1")
#     sound_src_model.add_element(sound_src_link)
#
#     sound_src_sdf = SDF()
#     sound_src_sdf.add_element(sound_src_model)
#
#     model_name = yield From(wait_for(world.insert_model_callback(sound_src_sdf)))
#
#     yield From(world.set_sound_update_frequency(update_frequency=0.5))
#     yield From(world.attach_sound_source(name=model_name, frequency=500))

    yield From(world.pause(False))

    while (True):
        if conf.trajectory_file != '':
            position = robot.last_position
            w_time = get_time(world)
            if w_time < conf.trajectory_limit or conf.trajectory_limit == 0:
                with open(conf.trajectory_file, 'a') as out_file:
                    out_file.write("{0},{1},{2},{3}\n".format(w_time, position[0], position[1], position[2]))

        yield From(trollius.sleep(0.1))



def get_time(world):
    if world.last_time:
        return world.last_time
    else:
        return 0


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
        print "FINISH"

    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")
    except ConnectionRefusedError:
        print("Connection refused, are the world and the analyzer loaded?")

if __name__ == '__main__':
    main()
