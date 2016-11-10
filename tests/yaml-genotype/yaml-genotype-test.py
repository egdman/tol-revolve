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

with open('output.yaml', 'w+') as outfile:
	outfile.write(genotype.to_yaml())

# print yaml_obj