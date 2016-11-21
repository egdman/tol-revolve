import yaml

# Revolve
from revolve.convert.yaml import yaml_to_robot

# ToL
from .convert import NeuralNetworkParser
from neat import GeneticEncoding



def robot_brain_to_tree(robot_yaml, brain_yaml, body_spec, brain_spec):

    # convert YAML stream to protobuf body:
    robot_body_pb = yaml_to_robot(body_spec, brain_spec, robot_yaml).body

    # convert YAML stream to genotype:
    # robot_brain_genotype = yaml_to_genotype(brain_yaml, brain_spec)
    robot_brain_genotype = GeneticEncoding().from_yaml(yaml.load(brain_yaml))

    # convert genotype to protobuf brain:
    nn_parser = NeuralNetworkParser(brain_spec)
    robot_brain_pb = nn_parser.genotype_to_brain(robot_brain_genotype)

    return robot_body_pb, robot_brain_pb

