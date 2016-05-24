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
        neuron_data_v['params'] = {"alpha" : 1.0, "tau" : 5.0, "energy" : 2.0}
        id_v = self._add_neuron(neuron_data_v, pb_brain)

        neuron_data_x = {}
        neuron_data_x['type'] = "X-Neuron"
        neuron_data_x['layer'] = 'hidden'
        neuron_data_x['partId'] = part_id
        neuron_data_x['params'] = {"tau" : 5.0}
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


    def _add_inter_CPG_connections(self, ids1, ids2, weight, pb_brain):
        id1_x = ids1['id_x']
        id2_x = ids2['id_x']

        id1_v = ids1['id_v']
        id2_v = ids1['id_v']

        conn_data1 = {'src': id1_x, 'dst': id2_v, 'weight': weight, 'socket': 'from_x_ext'}
        conn_data2 = {'src': id2_x, 'dst': id1_v, 'weight': weight, 'socket': 'from_x_ext'}

        conn_data3 = {'src': id1_v, 'dst': id2_v, 'weight': weight, 'socket': 'from_v_ext'}
        conn_data4 = {'src': id2_v, 'dst': id1_v, 'weight': weight, 'socket': 'from_v_ext'}

        self._add_connection(conn_data1, pb_brain)
        self._add_connection(conn_data2, pb_brain)
        self._add_connection(conn_data3, pb_brain)
        self._add_connection(conn_data4, pb_brain)


    def _parse_part(self, pb_part, pb_brain, cpg_stack, neuron_type):
        part_type = pb_part.type

        if part_type == 'ActiveHinge':
            cpg_ids = self._add_cpg(pb_part, pb_brain)
            cpg_stack.append(cpg_ids)



        connections = pb_part.child

        for connection in connections:
            next_part = connection.part
            self._parse_part(next_part, pb_brain, cpg_stack, neuron_type)

        # add inter-CPG connections (from x to v and from v to v)
        while len(cpg_stack) > 1:
            ids1 = cpg_stack[-1]
            ids2 = cpg_stack[-2]
            # self._add_inter_CPG_connections(ids1, ids2, 1.0, pb_brain)
            del cpg_stack[-1]
        if len(cpg_stack) == 1:
            self.root_nodes.append(cpg_stack[0])
            del cpg_stack[0]



    def add_CPGs(self, pb_robot, neuron_type):
        core = pb_robot.body.root
        brain = pb_robot.brain
        cpg_stack = []
        self._parse_part(core, brain, cpg_stack, neuron_type)

        # find all input neurons:
        input_neurons = []
        for n in brain.neuron:
            if n.layer == 'input':
                input_neurons.append(n)


        if len(self.root_nodes) != 0:

            # connect inputs to root neurons:
            for rn in self.root_nodes:
                for inp_n in input_neurons:
                    conn_data = {'src': inp_n.id, 'dst': rn['id_v'], 'weight': 1.0}
                    self._add_connection(conn_data, brain)

            # connect root nodes together:
            for i in range(len(self.root_nodes) - 1):
                rn1 = self.root_nodes[i]
                for j in range(i+1, len(self.root_nodes)):
                    rn2 = self.root_nodes[j]
                    self._add_inter_CPG_connections(rn1, rn2, weight=1.0, pb_brain=brain)




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
