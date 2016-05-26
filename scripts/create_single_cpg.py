import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from revolve.convert import yaml_to_robot, robot_to_yaml
from revolve.spec.exception import err

from tol.spec import get_body_spec, get_extended_brain_spec
from tol.config import parser

parser.add_argument( 'file_name', metavar='FILENAME', type=str, help='path to input YAML file')
parser.add_argument('-o', '--output', type=str, default='output.yaml', help='name of the output file')
parser.add_argument('--type', type=str, default='Simple', help="type of the neurons in the cpg")

"""
CPG model with nonlinear oscillators from Ijspeert's "Simulation and Robotics Studies of Salamander
Locomotion" (2005): 
"""


class CPG_Factory:
    def __init__(self, body_spec, brain_spec):
        self.num_neurons_added = 0
        self.body_spec = body_spec
        self.brain_spec = brain_spec
        self.root_nodes = []

    def _add_cpg(self, pb_part, pb_brain):
        part_id = pb_part.id

        neuron_data_v = {}
        neuron_data_v['type'] = "V-Neuron"
        neuron_data_v['layer'] = 'hidden'
        neuron_data_v['partId'] = part_id
        neuron_data_v['params'] = {"alpha" : 1.0, "tau" : 0.5, "energy" : 10.0}
        id_v = self._add_neuron(neuron_data_v, pb_brain)

        neuron_data_x = {}
        neuron_data_x['type'] = "X-Neuron"
        neuron_data_x['layer'] = 'hidden'
        neuron_data_x['partId'] = part_id
        neuron_data_x['params'] = {"tau" : 0.5}
        id_x = self._add_neuron(neuron_data_x, pb_brain)

        # neuron_data_q = {}
        # neuron_data_q['type'] = "QuadNeuron"
        # neuron_data_q['layer'] = 'hidden'
        # neuron_data_q['partId'] = part_id
        # neuron_data_q['params'] = {}
        # id_q = self._add_neuron(neuron_data_q, pb_brain)

        # mutual connections:
        xv_data = {'src': id_x, 'dst': id_v, 'weight': 1.0, 'socket': 'from_x'}
        vx_data = {'src': id_v, 'dst': id_x, 'weight': 1.0, 'socket': 'from_v'}

        # xq_data = {'src': id_x, 'dst': id_q, 'weight': 1.0}
        # qv_data = {'src': id_q, 'dst': id_v, 'weight': 1.0, 'socket': 'from_q'}

        # vq_data = {'src': id_v, 'dst': id_q, 'weight': 1.0}

        
        self._add_connection(xv_data, pb_brain)
        self._add_connection(vx_data, pb_brain)
        # self._add_connection(xq_data, pb_brain)
        # self._add_connection(qv_data, pb_brain)
        # self._add_connection(vq_data, pb_brain)

        # find output neuron:
        out_id = None
        for neuron in pb_brain.neuron:
            if neuron.partId == part_id and neuron.layer == 'output':
                out_id = neuron.id

        if out_id is not None:
            to_output_data = {'src': id_v, 'dst': out_id, 'weight': 1.0}
            self._add_connection(to_output_data, pb_brain)
        return {'id_v': id_v, 'id_x': id_x}



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
        if 'socket' in data:
            conn.socket = data['socket']


    def _add_double_connection(self, id1, id2, weight, pb_brain):
        conn_data1 = {'src': id1, 'dst': id2, 'weight': weight}
        conn_data2 = {'src': id2, 'dst': id1, 'weight': weight}
        self._add_connection(conn_data1, pb_brain)
        self._add_connection(conn_data2, pb_brain)


    def add_CPGs(self, pb_robot, neuron_type):
        core = pb_robot.body.root
        brain = pb_robot.brain

        # add single CPG to the core component
        cpg_ids = self._add_cpg(core, brain)

        # find all input neurons:
        input_neurons = []
        output_neurons = []
        for n in brain.neuron:
            if n.layer == 'input':
                input_neurons.append(n)
            elif n.layer == 'output':
                output_neurons.append(n)

        # connect inputs to the CPG:
        for in_neuron in input_neurons:
            conn_data = {'src': in_neuron.id, 'dst': cpg_ids['id_v'], 'weight': 0.0}
            self._add_connection(conn_data, brain)

        # connect the CPG to the outputs:
        for out_neuron in output_neurons:
            conn_data = {'src': cpg_ids['id_x'], 'dst': out_neuron.id, 'weight': 10.0}
            self._add_connection(conn_data, brain)
            


def main():
    conf = parser.parse_args()

    in_path = conf.file_name
    out_path = os.path.join(os.path.dirname(in_path), conf.output)

    with open(in_path,'r') as yamlfile:
        yaml_bot = yamlfile.read()

    body_spec = get_body_spec(conf)
    brain_spec = get_extended_brain_spec(conf)

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
