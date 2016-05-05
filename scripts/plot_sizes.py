import yaml
import random
import os
import fnmatch
from argparse import ArgumentParser
from matplotlib import pyplot as plt
import matplotlib.lines as mlines
import matplotlib.colors as colors
import matplotlib.cm as cmx


parser = ArgumentParser()

parser.add_argument('dir_path', metavar='DIR', type=str, help="Path to a genotype directory")
parser.add_argument('-t', '--title', type=str, default='plot title', help='Title of the plot')
parser.add_argument('-o', '--output', type=str, default='plot', help='Output file name')

parser.add_argument('--title-size', type=float, default=42, help='text size for the title')
parser.add_argument('--label-size', type=float, default=40, help='text size for the axis labels')
parser.add_argument('--legend-size', type=float, default=30, help='text size for the legend')
parser.add_argument('--tick-size', type=float, default=30, help='text size for the ticks')



def main():
    args = parser.parse_args()

    title_size = args.title_size
    label_size = args.label_size
    tick_size = args.tick_size
    legend_size = args.legend_size

    dir_path = args.dir_path
    out_file_path = os.path.join(dir_path, args.output)

    files_and_dirs = os.listdir(dir_path)
    files = [f for f in files_and_dirs if os.path.isfile(os.path.join(dir_path, f)) and
             fnmatch.fnmatch(f, 'gen_*_genotypes.log')]

    files = sorted(files, key=lambda item: int(item.split('_')[1]))

    generation_nums = []
    eval_nums = []
    neuron_counts = []
    conn_counts = []
    with open(out_file_path, 'w+') as out_file:
        out_file.write("generation,evaluation,neurons,connections\n")

    for filename in files:
        file_path = os.path.join(dir_path, filename)
        print "input :  {0}".format(file_path)


        with open(file_path, 'r') as in_file:
            yaml_data = in_file.read()
        data = yaml.load(yaml_data)
        num_brains = len(data)
        best_brain = data[0]
        neurons = best_brain['neurons']
        connections = best_brain['connections']

        gen_num = int(filename.split('_')[1]) + 1
        eval_num = gen_num * num_brains
        print "size: {0}".format(num_brains)
        print "generation: {0}".format(gen_num)

        num_neurons = len(neurons)
        num_connections = len(connections)

        generation_nums.append(gen_num)
        eval_nums.append(eval_num)
        neuron_counts.append(num_neurons)
        conn_counts.append(num_connections)

        with open(out_file_path, 'a') as out_file:
            out_file.write("{0},{1},{2},{3}\n".format(gen_num, eval_num, num_neurons, num_connections))


    # # plot raw data:
    # fig = plt.figure(figsize=(10, 12))
    # ax = fig.add_subplot(111)
    #
    # ax.plot(eval_nums, neuron_counts, linewidth=2,
    #                 label='number of neurons',
    #                 markevery=100)
    #
    # ax.legend(loc=0, prop={'size': legend_size})
    #
    # ax.tick_params(axis='both', which='major', labelsize=tick_size)
    # ax.set_title(args.title, fontsize=title_size, y=1.02)
    # xartist = ax.set_xlabel('evaluation #', fontsize=label_size)
    # yartist = ax.set_ylabel('fitness', fontsize=label_size)
    # ax.grid()
    # fig.savefig(out_file_path, bbox_extra_artists=(xartist, yartist), bbox_inches='tight')
    # # ##################################################################################################


if __name__ == '__main__':
    main()
