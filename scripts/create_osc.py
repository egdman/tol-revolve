import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from revolve.convert import yaml_to_robot, robot_to_yaml
from revolve.spec.exception import err

from tol.spec import get_body_spec, get_brain_spec
from tol.config import parser

parser.add_argument( 'file_name', metavar='FILENAME', type=str, help='path to input YAML file')
parser.add_argument('-o', '--output', type=str, default='output.yaml', help='name of the output file')
parser.add_argument('--type', type=str, default='Simple', help="type of the neurons in the cpg")

"""
This script creates simple Oscillator neuron for each joint.
"""

class CPG_Factory:
    def __init__(self, body_spec, brain_spec):
        self.num_neurons_added = 0
        self.body_spec = body_spec
        self.brain_spec = brain_spec
        self.root_nodes = []

    def _add_cpg(self, pb_part, pb_brain, neuron_type):
        part_id = pb_part.id

        neuron_data = {}
        neuron_data['type'] = 'Oscillator'
        neuron_data['layer'] = 'hidden'
        neuron_data['partId'] = part_id
        neuron_data['params'] = {"amplitude" : 10.0, "phase_offset" : 0.0, "period": 1.0}
        id_1 = self._add_neuron(neuron_data, pb_brain)

        # find output neuron:
        out_id = None
        for neuron in pb_brain.neuron:
            if neuron.partId == part_id and neuron.layer == 'output':
                out_id = neuron.id

        if out_id is not None:
            conn_out = {'src': id_1, 'dst': out_id, 'weight': 1.0}
            self._add_connection(conn_out, pb_brain)
        return id_1



    def _add_neuron(self, data, pb_brain):
        neuron = pb_brain.neuron.add()

        neuron.type = data['type']
        neuron.layer = data['layer']
        neuron.partId = data['partId']
        neuron.id = "{0}-cpg-{1}".format(neuron.partId, self.num_neurons_added)
        self.num_neurons_added += 1

        spec = self.brain_spec.get(neuron.type)
        if spec is None:
            err("Unknown neuron type '%s'" % neuron.type)

        param_dict = data['params']
        serial_params = spec.serialize_params(param_dict)

        for value in serial_params:
            param = neuron.param.add()
            param.value = value

        return neuron.id

    def _add_connection(self, data, pb_brain):
        conn = pb_brain.connection.add()
        conn.src = data['src']
        conn.dst = data['dst']
        conn.weight = data['weight']


    def _parse_part(self, pb_part, pb_brain, cpg_stack, neuron_type):
        part_type = pb_part.type

        if part_type == 'ActiveHinge':
            cpg_id = self._add_cpg(pb_part, pb_brain, neuron_type)
            cpg_stack.append(cpg_id)

        connections = pb_part.child

        for connection in connections:
            next_part = connection.part
            self._parse_part(next_part, pb_brain, cpg_stack, neuron_type)


    def add_CPGs(self, pb_robot, neuron_type):
        core = pb_robot.body.root
        brain = pb_robot.brain
        cpg_stack = []
        self._parse_part(core, brain, cpg_stack, neuron_type)


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
    cpg_factory.add_CPGs(pb_bot, conf.type)


    print "converting to yaml..."
    yaml_bot = robot_to_yaml(body_spec, brain_spec, pb_bot)

    with open(out_path,'w') as out_file:
        out_file.write(yaml_bot)

    print "done"



if __name__ == '__main__':
    main()
