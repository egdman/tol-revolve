import os
import sys
import yaml
import pygraphviz as pgv

from argparse import ArgumentParser

parser = ArgumentParser("draw_graphs.py")

parser.add_argument('dir_path', metavar='PATH', type=str, help="Path to a genotype log folder")

# parser.add_argument('-t', '--title', type=str, default='plot title', help='Title of the plot')


def draw_graph(in_file, out_file):
    with open(in_file, 'r') as input:
        data_yaml = input.read()
    data = yaml.load(data_yaml)
    node_count = data['node_count']
    edges = data['edges']

    graph = pgv.AGraph(strict=True, directed=False)
    for num in range(node_count):
        graph.add_node(str(num))

    for edge in edges:
        src = str(edge['src'])
        dst = str(edge['dst'])
        graph.add_edge(src, dst)

    graph.write(out_file+".dot")
    graph.layout()
    graph.draw(out_file+".png",)



def main():
    args = parser.parse_args()

    dir_path = args.dir_path
    out_dir_path = os.path.join(dir_path, "images")


    try:
        os.mkdir(out_dir_path)
    except OSError:
        print "Directory " + out_dir_path + " already exists."


    files_and_dirs = os.listdir(dir_path)
    files = [f for f in files_and_dirs if os.path.isfile(os.path.join(dir_path, f))]

    for gen_file in files:
        in_file = os.path.join(dir_path, gen_file)
        out_file = os.path.join(out_dir_path, gen_file)

        print 'input  : {0}'.format(in_file)
        print 'output : {0}'.format(out_file)

        draw_graph(in_file, out_file)


if __name__ == '__main__':
    main()
