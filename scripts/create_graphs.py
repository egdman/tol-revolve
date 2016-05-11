import os
import sys
import fnmatch
#import pygraphviz as pgv

from argparse import ArgumentParser

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')

from tol.learning import create_species_graph

parser = ArgumentParser("create_graphs.py")

parser.add_argument('dir_path', metavar='PATH', type=str, help="Path to a genotype log folder")
parser.add_argument('--threshold', type=float, default=0.5, help='speciation threshold')
parser.add_argument('-o', '--output', type=str, default="graphs", help='name of the output directory')
parser.add_argument('-p', '--pattern', type=str, default="gen_*_genotypes.log", help='input filename pattern')

# parser.add_argument('-t', '--title', type=str, default='plot title', help='Title of the plot')

def main():
    args = parser.parse_args()

    dir_path = args.dir_path
    spec_thr = args.threshold
    out_dir_path = os.path.join(dir_path, args.output)

    try:
        os.mkdir(out_dir_path)
    except OSError:
        print "Directory " + out_dir_path + " already exists."


    files_and_dirs = os.listdir(dir_path)
    files = [f for f in files_and_dirs if os.path.isfile(os.path.join(dir_path, f)) and
             fnmatch.fnmatch(f, args.pattern)]

    for gen_file in files:
        in_file = os.path.join(dir_path, gen_file)
        out_file = os.path.join(out_dir_path, gen_file + ".graph")

        print 'input  : {0}'.format(in_file)
        print 'output : {0}'.format(out_file)

        create_species_graph(in_file, out_file, spec_thr)


if __name__ == '__main__':
    main()
