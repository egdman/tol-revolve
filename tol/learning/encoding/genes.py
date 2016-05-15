import yaml
from copy import copy, deepcopy


def validate_genotype(genotype, err_message):
    if not genotype.check_validity():
        ex = GenotypeInvalidError(message=err_message, genotype=genotype)
        print ex.debug_string()
        raise RuntimeError
    return True


def unicode_representer(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data)


class Neuron:
    """
    This is all the info about a neuron
    """

    def __init__(self, neuron_id, layer, neuron_type, body_part_id, neuron_params):
        self.neuron_id = neuron_id
        self.layer = layer
        self.neuron_type = neuron_type
        self.body_part_id = body_part_id
        self.neuron_params = neuron_params

    def copy(self):
        copy_neuron = Neuron(neuron_id=copy(self.neuron_id),
                             layer=copy(self.layer),
                             neuron_type=copy(self.neuron_type),
                             body_part_id=copy(self.body_part_id),
                             neuron_params=deepcopy(self.neuron_params))
        return copy_neuron

    def __str__(self):
        return "id={0}, layer={1}, type={2}, part={3}".format(self.neuron_id, self.layer, self.neuron_type, self.body_part_id)



class Gene:
    def __init__(self, innovation_number=0, enabled=True):
        self.historical_mark = innovation_number
        self.enabled = enabled


class NeuronGene(Gene):
    def __init__(self, neuron, innovation_number=0, enabled=True):
        Gene.__init__(self, innovation_number = innovation_number,
                                       enabled = enabled)
        """
        :param neuron:
        :type neuron: Neuron

        :param innovation_number:
        :type innovation_number: int

        :param enabled:
        :type enabled: bool
        """

        self.neuron = neuron


    def __str__(self):
        return "NEAT Neuron gene, " + str(self.neuron) + ", mark " + str(self.historical_mark)


class ConnectionGene(Gene):
    def __init__(self, mark_from, mark_to, weight, innovation_number=0, enabled=True):
        Gene.__init__(self, innovation_number = innovation_number,
                                             enabled = enabled)

        """
        :param mark_from:
        :type mark_from: int

        :param mark_to:
        :type mark_to: int

        :param weight:
        :type weight: float

        :param innovation_number:
        :type innovation_number: int

        :param enabled:
        :type enabled: bool
        """
        self.mark_from = mark_from
        self.mark_to = mark_to
        self.weight = weight


    def __str__(self):
            return "NEAT Connection gene at " + hex(id(self)) + ",mark " + str(self.historical_mark) + \
                " (from " + str(self.mark_from) + " to " + str(self.mark_to) + ")"



class MutationRateGene(Gene):
    def __init__(self, rate, innovation_number=0, enabled=True):
        Gene.__init__(self, innovation_number=innovation_number,
                      enabled=enabled)
        self.rate = rate

    def __str__(self):
        return "NEAT Mutation rate gene at " + hex(id(self)) + ",mark " + str(self.historical_mark) + \
               " (rate=" + str(self.rate) + ")"



class GeneticEncoding:
    def __init__(self):
        self.neuron_genes = []
        self.connection_genes = []
    
    
    def num_genes(self):
        return len(self.neuron_genes) + len(self.connection_genes)

    
    def connection_exists(self, mark_from, mark_to):
        exists = False
        for c_g in self.connection_genes:
            if c_g.mark_from == mark_from and c_g.mark_to == mark_to and c_g.enabled:
                exists = True
                break

        return exists
    
    
    @staticmethod
    def get_dissimilarity(genotype1, genotype2, excess_coef=1, disjoint_coef=1, weight_diff_coef=1):
        excess_num, disjoint_num = GeneticEncoding.get_excess_disjoint(genotype1, genotype2)
        num_genes = max(genotype1.num_genes(), genotype2.num_genes())
        dissimilarity = float(disjoint_coef * disjoint_num + excess_coef * excess_num) / float(num_genes)

        # # FOR DEBUG:
        # ############################
        # print "disjoint = {0}".format(disjoint_num)
        # print "excess   = {0}".format(excess_num)
        # ############################

        return dissimilarity
        
        
    @staticmethod
    def get_excess_disjoint(genotype1, genotype2):
        genes_sorted1 = sorted(genotype1.neuron_genes + genotype1.connection_genes,
                               key = lambda gene: gene.historical_mark)

        genes_sorted2 = sorted(genotype2.neuron_genes + genotype2.connection_genes,
                               key = lambda gene: gene.historical_mark)

        min_mark1 = genes_sorted1[0].historical_mark
        max_mark1 = genes_sorted1[-1].historical_mark

        min_mark2 = genes_sorted2[0].historical_mark
        max_mark2 = genes_sorted2[-1].historical_mark
        
        pairs = GeneticEncoding.get_pairs(genes_sorted1, genes_sorted2)

        excess_num = 0
        disjoint_num = 0
        
        for pair in pairs:

            # # FOR DEBUG:
            # ############################
            # print "{0} :: {1}".format((pair[0].historical_mark if pair[0] else 'none'),
            #                           (pair[1].historical_mark if pair[1] else 'none'))
            # ############################

            if pair[0] and not pair[1]:
                mark = pair[0].historical_mark
                if mark > (min_mark2 - 1) and mark < (max_mark2 + 1):
                    disjoint_num += 1
                else:
                    excess_num += 1
                    
            elif pair[1] and not pair[0]:
                mark = pair[1].historical_mark
                if mark > (min_mark1 - 1) and mark < (max_mark1 + 1):
                    disjoint_num += 1
                else:
                    excess_num += 1
        
        return excess_num, disjoint_num


    @staticmethod
    def get_pairs(genes_sorted1, genes_sorted2):
        num_genes1 = len(genes_sorted1)
        num_genes2 = len(genes_sorted2)

        min_mark1 = genes_sorted1[0].historical_mark
        max_mark1 = genes_sorted1[-1].historical_mark

        min_mark2 = genes_sorted2[0].historical_mark
        max_mark2 = genes_sorted2[-1].historical_mark

        min_mark = min(min_mark1, min_mark2)
        max_mark = max(max_mark1, max_mark2)
        
        
        gene_pairs = []

        # search for pairs of genes with equal marks:
        start_from1 = 0
        start_from2 = 0

        mark = min_mark
        while mark < max_mark + 1:

            # jump1 and jump2 are here to skip long sequences of empty historical marks

            gene1 = None
            jump1 = mark + 1
            for i in range(start_from1, num_genes1):
                if genes_sorted1[i].historical_mark == mark:
                    gene1 = genes_sorted1[i]
                    start_from1 = i
                    break

                # if there is a gap, jump over it:
                elif genes_sorted1[i].historical_mark > mark:
                    jump1 = genes_sorted1[i].historical_mark
                    start_from1 = i
                    break

                # if the end of the gene sequence is reached:
                elif i == num_genes1 - 1:
                    jump1 = max_mark + 1
                    start_from1 = i

            gene2 = None
            jump2 = mark + 1
            for i in range(start_from2, num_genes2):
                if genes_sorted2[i].historical_mark == mark:
                    gene2 = genes_sorted2[i]
                    start_from2 = i
                    break

                # if there is a gap, jump over it:
                elif genes_sorted2[i].historical_mark > mark:
                    jump2 = genes_sorted2[i].historical_mark
                    start_from2 = i
                    break

                # if the end of the gene sequence is reached:
                elif i == num_genes2 - 1:
                    jump2 = max_mark + 1
                    start_from2 = i

            # # FOR DEBUG:
            # #####################################################
            # print "mark = {0}, {1} :: {2}".format(mark,
            #         "-" if gene1 is None else "+",
            #         "-" if gene2 is None else "+")
            # #####################################################

            # do not add a pair if both genes are None:
            if gene1 or gene2:
                gene_pairs.append((gene1, gene2))

            mark = min(jump1, jump2)
#            mark += 1
            
        return gene_pairs


    @staticmethod
    def get_space_dimensionality(genotypes, brain_spec):
        '''
        this method returns the list of pairs (historical mark, number of parameters for that gene)
        for those genes that are not present, the number of parameters is zero

        :param genotypes:
        :param brain_spec:
        :return:
        '''

        sorted_gene_lists = []
        for genotype in genotypes:
            sorted_gene_list = genotype.get_sorted_genes()
            sorted_gene_lists.append(sorted_gene_list)




        glob_min_hm = sorted_gene_lists[0][0].historical_mark
        glob_max_hm = sorted_gene_lists[0][-1].historical_mark

        for gene_list in sorted_gene_lists:
            min_hm = gene_list[0].historical_mark
            max_hm = gene_list[-1].historical_mark

            if min_hm < glob_min_hm:
                glob_min_hm = min_hm

            if max_hm > glob_max_hm:
                glob_max_hm = max_hm


        hm_param_numbers = []
        for hm in range(0, glob_max_hm + 1):
            this_gene = None
            for gene_list in sorted_gene_lists:
                for gene in gene_list:
                    if gene.historical_mark == hm:
                        this_gene = gene
                        break
                    elif gene.historical_mark > hm:
                        break
            if this_gene is None:
                hm_param_numbers.append((hm, 0))
            else:
                if isinstance(this_gene, ConnectionGene):

                    hm_param_numbers.append((hm, 1))
                elif isinstance(this_gene, NeuronGene):
                    neuron_type = this_gene.neuron.neuron_type
                    neuron_spec = brain_spec.get(neuron_type)
                    num_params = len(neuron_spec.parameters)
                    hm_param_numbers.append((hm, num_params))

        return hm_param_numbers


    def to_vector(self, hm_param_numbers, brain_spec):
        vector = []
        sorted_genes = self.get_sorted_genes()

        for (cur_hm, par_num) in hm_param_numbers:

            if par_num == 0:
                continue

            this_gene = None

            for gene in sorted_genes:
                hm = gene.historical_mark

                # if we have that gene
                if hm == cur_hm:
                    this_gene = gene

                # if we don't have that gene
                elif hm > cur_hm:
                    break

            # if we don't have this gene, fill in zeros:
            if this_gene is None:
                for j in range(par_num):
                    vector.append(0)

            # if we do have this gene, fill in parameter values:
            elif isinstance(this_gene, ConnectionGene):
                weight = this_gene.weight
                vector.append(weight)
            elif isinstance(this_gene, NeuronGene):
                neuron_spec = brain_spec.get(this_gene.neuron.neuron_type)
                ser_params = neuron_spec.serialize_params(this_gene.neuron.neuron_params)
                for val in ser_params:
                    vector.append(val)

        return vector


    def from_vector(self, vector, hm_param_numbers, brain_spec):
        sorted_genes = self.get_sorted_genes()
        base_index = 0
        for (cur_hm, par_num) in hm_param_numbers:

            if par_num == 0:
                continue

            this_gene = None

            for gene in sorted_genes:

                hm = gene.historical_mark

                # if we have that gene
                if hm == cur_hm:
                    this_gene = gene

                # if we don't have that gene
                elif hm > cur_hm:
                    break

            if this_gene is not None:
                this_gene_params = []
                for i in range(base_index, base_index + par_num):
                    this_gene_params.append(vector[i])
                if isinstance(this_gene, ConnectionGene):
                    this_gene.weight = this_gene_params[0]
                elif isinstance(this_gene, NeuronGene):
                    neuron_spec = brain_spec.get(this_gene.neuron.neuron_type)

                    neuron_params = {}
                    for par_name in neuron_spec.parameters:
                        par_index = neuron_spec.parameters[par_name][0]
                        neuron_params[par_name] = this_gene_params[par_index]

                    this_gene.neuron.neuron_params = neuron_params

            base_index += par_num


    def get_sorted_genes(self):
        return sorted(self.neuron_genes + self.connection_genes,
                        key = lambda gene: gene.historical_mark)

    def min_max_hist_mark(self):
        genes_sorted = sorted(self.neuron_genes + self.connection_genes,
                        key = lambda gene: gene.historical_mark)

        return genes_sorted[0].historical_mark, genes_sorted[-1].historical_mark


    def find_gene_by_mark(self, mark):
        for gene in self.neuron_genes + self.connection_genes:
            if gene.historical_mark == mark:
                return gene
        return None


    def add_neuron_gene(self, neuron_gene):
        self.neuron_genes.append(neuron_gene)


    def add_connection_gene(self, connection_gene):
        self.connection_genes.append(connection_gene)


    def remove_connection_gene(self, index):
        del self.connection_genes[index]


    def remove_neuron_gene(self, index):
        del self.neuron_genes[index]


    def to_lists(self):
        neuron_list = []
        for neuron_gene in self.neuron_genes:
            neuron = neuron_gene.neuron
            neuron_list.append({
                "hist_mark": neuron_gene.historical_mark,
                "enabled": neuron_gene.enabled,
                "id": neuron.neuron_id,
                "layer": neuron.layer,
                "type": neuron.neuron_type,
                "part_id": neuron.body_part_id,
                "params": neuron.neuron_params
            })

        conn_list = []
        for conn_gene in self.connection_genes:
            conn_list.append({
                "hist_mark": conn_gene.historical_mark,
                "enabled": conn_gene.enabled,
                "from": conn_gene.mark_from,
                "to": conn_gene.mark_to,
                "weight": conn_gene.weight
            })

        return neuron_list, conn_list


    def debug_string(self, verbose=False):
        deb_str = ""
        if verbose:
            n_gs, c_gs = self.to_lists()
            deb_str += "neurons:\n"
            for n_g in n_gs:
                deb_str += str(n_g)
                deb_str += "\n"
            deb_str += "connections:\n"
            for c_g in c_gs:
                deb_str += str(c_g)
                deb_str += "\n"

        else:
            n_gs, c_gs = self.to_lists()
            deb_str += "neurons:\n"
            for n_g in n_gs:
                deb_str += "("
                deb_str += str(n_g["id"]) + ", mark="
                deb_str += str(n_g["hist_mark"])
                deb_str += ")"
            deb_str += "\nconnections:\n"
            for c_g in c_gs:
                deb_str += "["
                deb_str += str(c_g["from"])
                deb_str += ", "
                deb_str += str(c_g["to"])
                deb_str += "]"

        return deb_str


    def to_yaml(self):
        neuron_genes, conn_genes = self.to_lists()
        yaml.add_representer(unicode, unicode_representer)
        yaml_brain = {}
        yaml_brain['neurons'] = neuron_genes
        yaml_brain['connections'] = conn_genes
        return yaml.dump(yaml_brain, default_flow_style=False)


    def copy(self):
        copy_gen = GeneticEncoding()
        old_to_new = {}

        for n_gene in self.neuron_genes:

            new_n_gene = NeuronGene(
                    neuron=n_gene.neuron.copy(),
                    innovation_number=n_gene.historical_mark,
                    enabled=n_gene.enabled)

            old_to_new[n_gene.neuron] = new_n_gene.neuron
            copy_gen.add_neuron_gene(new_n_gene)


        for c_gene in self.connection_genes:

            new_c_gene = ConnectionGene(
                    mark_from=c_gene.mark_from,
                    mark_to= c_gene.mark_to,
                    weight=c_gene.weight,
                    innovation_number=c_gene.historical_mark,
                    enabled=c_gene.enabled)
            copy_gen.add_connection_gene(new_c_gene)

        return copy_gen


    def check_validity(self):
        for conn_gene in self.connection_genes:
            mark_from = conn_gene.mark_from
            mark_to = conn_gene.mark_to
            if not self.check_neuron_exists(mark_from):
                return False
            if not self.check_neuron_exists(mark_to):
                return False
        return True


    def check_neuron_exists(self, mark):
        result = False
        for neuron_gene in self.neuron_genes:
            if mark == neuron_gene.historical_mark:
                result = True
        return result


    def __str__(self):
        return "NEAT Genotype at " + hex(id(self))



class GenotypeCopyError(Exception):
    def __init__(self, message, genotype):
        self.message = message
        self.genotype = genotype
    def debug_string(self):
        print "--------------------------"
        print self.message
        print "Tried to copy this genotype:"
        print "neurons:"
        for n_g in self.genotype.neuron_genes:
            print str(n_g) + ": " + str(n_g.neuron)
        print "connections:"
        for c_g in self.genotype.connection_genes:
            print c_g
        print "--------------------------"


class GenotypeInvalidError(Exception):
    def __init__(self, message, genotype):
        self.message = message
        self.genotype = genotype

    def debug_string(self):
        print "--------------------------"
        print self.message
        print "Invalid genotype:"
        print "neurons:"
        for n_g in self.genotype.neuron_genes:
            print n_g
        print "connections:"
        for c_g in self.genotype.connection_genes:
            print c_g
        print "--------------------------"