import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from revolve.convert import yaml_to_robot, robot_to_yaml
from revolve.spec.exception import err

from tol.spec import get_body_spec, get_brain_spec
from tol.config import parser

parser.add_argument( 'file_name', metavar='FILENAME', type=str, help='path to input YAML file')
parser.add_argument('-o', '--output', type=str, default='output.yaml', help='name of the output file')

class CPG_Factory:
    def __init__(self, body_spec, brain_spec):
        self.num_neurons_added = 0
        self.body_spec = body_spec
        self.brain_spec = brain_spec

    def _add_cpg(self, pb_part, pb_brain):
        neuron = pb_brain.neuron.add()
        part_id = pb_part.id
        neuron.id = "{0}-cpg-{1}".format(part_id, self.num_neurons_added)
        self.num_neurons_added += 1

        neuron.type = "Simple"
        neuron.layer = 'hidden'

        neuron.partId = part_id

        spec = self.brain_spec.get(neuron.type)
        if spec is None:
            err("Unknown neuron type '%s'" % neuron.type)

        param_dict = {"Bias" : 0.0, "Gain" : 0.5}

        serial_params = spec.serialize_params(param_dict)

        for value in serial_params:
            param = neuron.param.add()
            param.value = value



    def _parse_part(self, pb_part, pb_brain):
        part_type = pb_part.type

        if part_type == 'ActiveHinge':
            self._add_cpg(pb_part, pb_brain)

        connections = pb_part.child

        for connection in connections:
            next_part = connection.part
            self._parse_part(next_part, pb_brain)

    def add_CPGs(self, pb_robot):
        core = pb_robot.body.root
        brain = pb_robot.brain
        self._parse_part(core, brain)





def main():
    conf = parser.parse_args()

    in_path = conf.file_name
    out_path = os.path.join(os.path.dirname(in_path), conf.output)

    with open(in_path,'r') as yamlfile:
        yaml_bot = yamlfile.read()

    body_spec = get_body_spec(conf)
    brain_spec = get_brain_spec(conf)

    print "converting to protobuf..."
    pb_bot = yaml_to_robot(body_spec, brain_spec, yaml_bot)

    cpg_factory = CPG_Factory(body_spec=body_spec, brain_spec=brain_spec)
    cpg_factory.add_CPGs(pb_bot)


    print "converting to yaml..."
    yaml_bot = robot_to_yaml(body_spec, brain_spec, pb_bot)

    with open(out_path,'w') as out_file:
        out_file.write(yaml_bot)

    print "done"



if __name__ == '__main__':
    main()
