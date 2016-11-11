import sys
import os
import yaml

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")

from tol.learning.convert import yaml_to_genotype, NeuralNetworkParser
from tol.spec import get_extended_brain_spec
from tol.config import parser


conf = parser.parse_args()
brain_spec = get_extended_brain_spec(conf)

yaml_raw = open('input.yaml', 'r').read()

genotype = yaml_to_genotype(yaml_raw, brain_spec, True)

# print genotype

nn_parser = NeuralNetworkParser(brain_spec)
pb_nn = nn_parser.genotype_to_brain(genotype)


# print pb_nn
with open('output.pb', 'w+') as outfile:
	outfile.write(str(pb_nn))
# print yaml_obj