import argparse
import yaml
from neat import GeneticEncoding

from .spec import get_brain_spec



def get_brains_from_file(brain_file_path, brain_spec):
    '''
    generate a population of brains by reading them from a file
    :param brain_file:
    :return:
    '''

    with open(brain_file_path, 'r') as brain_file:
        yaml_str = brain_file.read()

    yaml_list = yaml.load(yaml_str)
    brain_list = list(GeneticEncoding().from_yaml(yaml_brain) for yaml_brain in yaml_list)


    # find min and max historical marks:
    min_mark, max_mark = brain_list[0].min_max_hist_mark()
    for br in brain_list:
        loc_min, loc_max = br.min_max_hist_mark()
        if loc_min < min_mark:
            min_mark = loc_min

        if loc_max > max_mark:
            max_mark = loc_max

    return brain_list, min_mark, max_mark



def create_species_graph(brain_file_path, output_file_path, speciation_threshold):
    conf = argparse.Namespace()
    conf.brain_mutation_epsilon = 1.0
    brain_spec = get_brain_spec(conf)

    brains, min_mark, max_mark = get_brains_from_file(brain_file_path, brain_spec)

    node_count = len(brains)
    edges = []

    for i in range(node_count-1):
        for j in range(i+1, node_count):

            dist = GeneticEncoding.get_dissimilarity(brains[i], brains[j])
            if dist < speciation_threshold:
                edges.append((i,j))

    with open(output_file_path, 'w+') as out_file:
        out_file.write('node_count:  {0}\n'.format(node_count))
        out_file.write('edges:\n')
        for edge in edges:
            out_file.write('  - src:  {0}\n'.format(edge[0]))
            out_file.write('    dst:  {0}\n'.format(edge[1]))
