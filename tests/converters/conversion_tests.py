import sys
import os
import yaml

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")

from tol.learning.convert import yaml_to_genotype, NeuralNetworkParser
from tol.spec import get_extended_brain_spec, get_extended_mutation_spec
from tol.config import parser
from neat import Mutator


conf = parser.parse_args()
brain_spec = get_extended_brain_spec(conf)

yaml_raw = open('input.yaml', 'r').read()

print("YAML -> genotype")
genotype = yaml_to_genotype(yaml_raw, brain_spec, True)

with open('output.yaml', 'w+') as outfile:
	outfile.write(genotype.to_yaml())

print("genotype: {} neurons, {} connections".format(
	len(genotype.neuron_genes),
	len(genotype.connection_genes)))

print("genotype -> protobuf")
nn_parser = NeuralNetworkParser(brain_spec)
pb_brain = nn_parser.genotype_to_brain(genotype)


with open('output.pb', 'w+') as outfile:
	outfile.write(str(pb_brain))



print("protobuf: {} neurons, {} connections".format(
	len(pb_brain.neuron),
	len(pb_brain.connection)))


print("protobuf -> genotype")
genotype = nn_parser.brain_to_genotype(pb_brain, Mutator(get_extended_mutation_spec(0.25, 5.0)))


print("genotype: {} neurons, {} connections".format(
	len(genotype.neuron_genes),
	len(genotype.connection_genes)))


with open('output.pb.yaml', 'w+') as outfile:
	outfile.write(genotype.to_yaml())