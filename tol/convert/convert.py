# Revolve
from revolve.spec.msgs.neural_net_pb2 import NeuralNetwork
from revolve.spec.exception import err

# ToL
from neat import GeneticEncoding


def add_missing_params(genotype):
    for neuron_gene in genotype.neuron_genes:
        # new ids are of the form 'augmentN', where N is the historical mark of the neuron
        if not hasattr(neuron_gene, 'id'):
            neuron_gene.id = 'augment{}'.format(neuron_gene.historical_mark)

        # the layer of new neurons is always hidden
        if not hasattr(neuron_gene, 'layer'):
            neuron_gene.layer = 'hidden'

        # TODO:
        # the way to determine part_ids of new neurons is yet to be devised
        if not hasattr(neuron_gene, 'part_id'):
            neuron_gene.part_id = 'Core'




class NeuralNetworkParser:

    def __init__(self, spec):
        self.spec = spec



    def _parse_pb_neurons(self, pb_neurons):
        neuron_map = []

        for pb_neuron in pb_neurons:
            neuron_type = pb_neuron.type

            neuron_id = pb_neuron.id
            neuron_layer = pb_neuron.layer
            neuron_part_id = pb_neuron.partId


            if neuron_id in neuron_map:
                err("Duplicate neuron ID '%s'" % neuron_id)


            neuron_spec = self.spec.get(neuron_type)
            if neuron_spec is None:
                err("Unknown neuron type '%s'" % neuron_type)


            neuron_params = neuron_spec.unserialize_params(pb_neuron.param)
            neuron_params.update(
                {
                    'id' : neuron_id,
                    'part_id'   : neuron_part_id,
                    'layer'     : neuron_layer,
                }    
            )


            neuron_map.append((neuron_id, neuron_type, neuron_params))

        return neuron_map



    def brain_to_genotype(self, pb_brain, mutator, protect):

        pb_neurons = pb_brain.neuron
        pb_connections = pb_brain.connection

        neuron_map = self._parse_pb_neurons(pb_neurons)

        genotype = GeneticEncoding()

        # map neuron ids to historical marks of their respective genes:
        id_mark_map = {}

        for neuron_id, neuron_type, neuron_params in neuron_map:
            layer = neuron_params["layer"]
            is_input = layer == "input"
            is_output = layer == "output"

            mark = mutator.add_neuron(genotype, neuron_type, protected = is_input or is_output, **neuron_params)
            id_mark_map[neuron_id] = mark
            # if protect: mutator.protect_gene(mark)


        for pb_connection in pb_connections:
            other_params = {}
            if pb_connection.HasField('socket'):
                other_params['socket'] = pb_connection.socket


            mark = mutator.add_connection(
                genotype,
                connection_type='default',
                mark_from=id_mark_map[pb_connection.src],
                mark_to=id_mark_map[pb_connection.dst],
                weight=pb_connection.weight,
                **other_params
            )
            # if protect: mutator.protect_gene(mark)

        return genotype






    def genotype_to_modify_msg(self, genotype):
        pb_brain = self.genotype_to_brain(genotype)
        msg = NeuralNetwork()
        pb_neurons = pb_brain.neuron
        pb_connections = pb_brain.connection

        # add only hidden neurons
        for pb_neuron in pb_neurons:
            if pb_neuron.layer == "hidden":
                added_neuron = msg.neuron.add()
                added_neuron.CopyFrom(pb_neuron)

        for pb_connection in pb_connections:
            added_connection = msg.connection.add()
            added_connection.CopyFrom(pb_connection)
        return msg






    def genotype_to_brain(self, genotype):
        # new neurons will come without ids, layers and part_ids, so we provide defaults
        add_missing_params(genotype)

        pb_brain = NeuralNetwork()

        self._parse_neuron_genes(genotype, pb_brain)
        self._parse_connection_genes(genotype, pb_brain)

        return pb_brain






    def _parse_neuron_genes(self, genotype, pb_brain):

        for neuron_gene in genotype.neuron_genes:

            neuron_params = neuron_gene.copy_params()
            pb_neuron = pb_brain.neuron.add()
            pb_neuron.type      = neuron_gene.gene_type
            pb_neuron.id        = neuron_params.pop('id')
            pb_neuron.layer     = neuron_params.pop('layer')
            pb_neuron.partId    = neuron_params.pop('part_id')

            # serialize the remaining params and put them into the protobuf 'param' attribute
            neuron_spec = self.spec.get(neuron_gene.gene_type)
            serialized_params = neuron_spec.serialize_params(neuron_params)

            # add parameter names and values
            for param_name, param_value in neuron_params.items():
                pb_param = pb_neuron.param.add()
                pb_param.name = param_name
                pb_param.value = param_value



    def _parse_connection_genes(self, genotype, pb_brain):
        def find_gene(genes, mark):
            return next((g for g in genes if g.historical_mark == mark), None)

        for conn_gene in genotype.connection_genes:
            mark_from = conn_gene.mark_from
            mark_to = conn_gene.mark_to

            from_id = find_gene(genotype.neuron_genes, mark_from).id
            to_id   = find_gene(genotype.neuron_genes, mark_to  ).id

            pb_conn = pb_brain.connection.add()
            pb_conn.src = from_id
            pb_conn.dst = to_id
            pb_conn.weight = conn_gene.weight

            # add 'socket' property if found in gene
            try:
                pb_conn.socket = conn_gene.socket
            except AttributeError:
                pass
