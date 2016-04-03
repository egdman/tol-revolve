import random

from . import NeuronGene, ConnectionGene, GeneticEncoding, Neuron, GenotypeCopyError, validate_genotype



class Mutator:

    def __init__(self, brain_spec, new_connection_sigma = 1, innovation_number = 0, max_attempts = 100):
        self.innovation_number = innovation_number
        self.new_connection_sigma = new_connection_sigma
        self.max_attempts = max_attempts
        self.brain_spec = brain_spec


    def mutate_neuron_params(self, genotype, probability, sigma):
        """
        Each neuron gene is chosen to be mutated with probability.
        The parameter to be mutated is chosen from the set of parameters with equal probability.
        """

        for neuron_gene in genotype.neuron_genes:
            if random.random() < probability:

                # # FOR DEBUG
                # ##################################
                # print 'mutating gene :{0}'.format(neuron_gene.neuron.neuron_id)
                # ##################################

                neuron_spec = self.brain_spec.get(neuron_gene.neuron.neuron_type)
                neuron_params = neuron_spec.parameters

                if neuron_params:
                    param_name, param_tuple = random.choice(neuron_params.items())
                    param_spec = param_tuple[1]
                    param_value = neuron_gene.neuron.neuron_params[param_name]
                    max_value = param_spec.max
                    min_value = param_spec.min
                    param_value += random.gauss(0, sigma)

                    if param_value > max_value:
                        if param_spec.max_inclusive:
                            param_value = max_value
                        else:
                            param_value = max_value - param_spec.epsilon

                    if param_value < min_value:
                        if param_spec.min_inclusive:
                            param_value = min_value
                        else:
                            param_value = min_value + param_spec.epsilon

                    # # FOR DEBUG
                    # ##################################
                    # print 'mutating param: {0} -- old value = {1}, new value = {2}'.\
                    #     format(param_name, neuron_gene.neuron.neuron_params[param_name], param_value)
                    # ##################################

                    neuron_gene.neuron.neuron_params[param_name] = param_value


    def mutate_weights(self, genotype, probability, sigma):

        """
        For every connection gene change weight with probability.
        The change value is drawn from normal distribution with mean=0 and sigma

        :type genotype: GeneticEncoding
        """
        for connection_gene in genotype.connection_genes:
            if random.random() < probability:
                weight_change = random.gauss(0, sigma)
                connection_gene.weight += weight_change


    def mutate_structure(self, genotype, probability):
        """
        Mutates structure of the neural network. Adds new neurons and connections.
        Chooses whether to apply a mutation with specified probability.
        Chooses what kind of mutation to apply (new connection of new neuron)
        with probability=0.5
        However, if there are no connections at all, always adds a connection.

        :type genotype: GeneticEncoding
        """

        if random.random() < probability:
            if len(genotype.connection_genes) == 0:
                self.add_connection_mutation(genotype, self.new_connection_sigma)
            else:
                if random.random() < 0.5:
                    self.add_connection_mutation(genotype, self.new_connection_sigma)
                else:
                    self.add_neuron_mutation(genotype)


    def add_connection_mutation(self, genotype, sigma):

        """
        Pick two neurons A and B at random. Make sure that connection AB does not exist.
        Also make sure that A is not output and B is not input.
        If those conditions are satisfied, add new connection whose weight is drawn from
        normal distribution with mean=0 and sigma.

        Otherwise pick two neurons again and repeat until suitable pair is found
        or we run out of attempts.

        :type genotype: GeneticEncoding
        :type sigma: float
        """

        neuron_from = random.choice(genotype.neuron_genes)
        neuron_to = random.choice(genotype.neuron_genes)
        mark_from = neuron_from.historical_mark
        mark_to = neuron_to.historical_mark

        num_attempts = 1

        # disallow incoming connections to input neurons:
        # also disallow connections starting from output neurons:
        while genotype.connection_exists(mark_from, mark_to) or \
                        neuron_to.neuron.layer == "input" or neuron_from.neuron.layer == "output":
            neuron_from = random.choice(genotype.neuron_genes)
            neuron_to = random.choice(genotype.neuron_genes)
            mark_from = neuron_from.historical_mark
            mark_to = neuron_to.historical_mark

            num_attempts += 1
            if num_attempts >= self.max_attempts:
                return False

        self.add_connection(mark_from, mark_to, weight = random.gauss(0, sigma), genotype = genotype)

        return True


    def add_neuron_mutation(self, genotype):

        """
        Pick a connection at random from neuron A to neuron B.
        And add a neuron C in between A and B.
        Old connection AB becomes disabled.
        Two new connections AC and CB are added.
        Weight of AC = weight of AB.
        Weight of CB = 1.0

        :type genotype: GeneticEncoding
        """

        connection_to_split = random.choice(genotype.connection_genes)
        old_weight = connection_to_split.weight
        connection_to_split.enabled = False

        mark_from = connection_to_split.mark_from
        mark_to = connection_to_split.mark_to

        neuron_from = genotype.find_gene_by_mark(mark_from).neuron
        neuron_to = genotype.find_gene_by_mark(mark_to).neuron

        # TODO make so that new neuron can be added anywhere along the path
        body_part_id = random.choice([neuron_from.body_part_id, neuron_to.body_part_id])

        new_neuron_types = ["Simple", "Sigmoid", "Oscillator"]

        new_neuron_type = random.choice(new_neuron_types)

        new_neuron_params = self.brain_spec.get(new_neuron_type).\
                    get_random_parameters(serialize=False) # returns dictionary {param_name:param_value}

        neuron_middle = Neuron(
            neuron_id="augment" + str(self.innovation_number),
            neuron_type=new_neuron_type,
            layer="hidden",
            body_part_id=body_part_id,
            neuron_params=new_neuron_params
        )

        mark_middle = self.add_neuron(neuron_middle, genotype)
        self.add_connection(mark_from, mark_middle, old_weight, genotype)
        self.add_connection(mark_middle, mark_to, 1.0, genotype)




    def add_neuron(self, neuron, genotype):
        new_neuron_gene = NeuronGene(neuron,
                                innovation_number = self.innovation_number,
                                enabled = True)
        self.innovation_number += 1
        genotype.add_neuron_gene(new_neuron_gene)
        return new_neuron_gene.historical_mark


    def add_connection(self, mark_from, mark_to, weight, genotype):
        new_conn_gene = ConnectionGene(mark_from, mark_to,
                                  weight = weight,
                                  innovation_number = self.innovation_number,
                                  enabled = True)
        self.innovation_number += 1
        genotype.add_connection_gene(new_conn_gene)
        return new_conn_gene.historical_mark


class Crossover:

    @staticmethod
    def crossover(genotype_more_fit, genotype_less_fit):
        # copy original genotypes to keep them intact:
        try:
            genotype_more_fit = genotype_more_fit.copy()
            genotype_less_fit = genotype_less_fit.copy()
        except GenotypeCopyError as ex:
            print ex.debug_string()
            raise RuntimeError


        # validate_genotype(genotype_more_fit, "crossover: copying created invalid genotype")
        # validate_genotype(genotype_less_fit, "crossover: copying created invalid genotype")

        # sort genes by historical marks:
        genes_better = sorted(genotype_more_fit.neuron_genes + genotype_more_fit.connection_genes,
                        key = lambda gene: gene.historical_mark)

        genes_worse = sorted(genotype_less_fit.neuron_genes + genotype_less_fit.connection_genes,
                        key = lambda gene: gene.historical_mark)

        gene_pairs = GeneticEncoding.get_pairs(genes_better, genes_worse)

        child_genes = []

        for pair in gene_pairs:

            # if gene is paired, inherit one of the pair with 50/50 chance:
            if pair[0] is not None and pair[1] is not None:
                if random.random() < 0.5:
                    child_genes.append(pair[0])
                else:
                    child_genes.append(pair[1])

            # inherit unpaired gene from the more fit parent:
            elif pair[0] is not None:
                child_genes.append(pair[0])


        # # FOR DEBUG
        # ############################################
        # print "CHILD GENES:"
        # for gene in child_genes:
        #     print str(gene)
        # ############################################


        child_genotype = GeneticEncoding()
        for gene in child_genes:
            if isinstance(gene, NeuronGene):
                child_genotype.add_neuron_gene(gene)
            elif isinstance(gene, ConnectionGene):
                child_genotype.add_connection_gene(gene)

        return child_genotype