import yaml
import random
import os
from argparse import ArgumentParser
from matplotlib import pyplot as plt
import matplotlib.lines as mlines
import matplotlib.colors as colors
import matplotlib.cm as cmx


parser = ArgumentParser("plot_fitness.py")

parser.add_argument('dir_path', metavar='DIR', type=str, help="Path to a fitness log file")
parser.add_argument('-t', '--title', type=str, default='plot title', help='Title of the plot')
parser.add_argument('-o', '--output', type=str, default='plot', help='Output file name')

parser.add_argument('--title-size', type=float, default=42, help='text size for the title')
parser.add_argument('--label-size', type=float, default=40, help='text size for the axis labels')
parser.add_argument('--legend-size', type=float, default=30, help='text size for the legend')
parser.add_argument('--tick-size', type=float, default=30, help='text size for the ticks')

def mean(values_list):
    return float(sum(values_list)) / float(len(values_list)) if len(values_list) > 0 else float('nan')

def median(values_list):
    num = len(values_list)
    if num % 2 == 0:
        val1 = values_list[num/2 - 1]
        val2 = values_list[num/2]
        median = float(val1 + val2) / 2.0
    else:
        median = values_list[(num-1) / 2]
    return median


def main():
    args = parser.parse_args()

    title_size = args.title_size
    label_size = args.label_size
    tick_size = args.tick_size
    legend_size = args.legend_size

    dir_path = args.dir_path
    out_file_path = os.path.join(dir_path, args.output)

    files_and_dirs = os.listdir(dir_path)
    files = [f for f in files_and_dirs if os.path.isfile(os.path.join(dir_path, f))]




    map_data_to_labels = {}

    color_map = {} # dictionary {label:color} because we want the same labels have the same color


    for filename in files:
        file_path = os .path.join(dir_path, filename)
        print "input :  {0}".format(file_path)

        with open(file_path, 'r') as in_file:
            yaml_data = in_file.read()

        label = filename.split('-')[-2]
        print 'label : {0}'.format(label)


        data = yaml.load(yaml_data)
        data_items = [(data_item['generation'], data_item['velocities']) for data_item in data]
        data_items = sorted(data_items, key=lambda pair: pair[0])

        generation_num = []
        evaluation_num = []
        max_val = []
#
        for i in range(len(data_items)):

            gen = data_items[i][0]
            velocities = data_items[i][1]
            generation_num.append(gen+1)
            evaluation_num.append((gen+1) * len(velocities))
            max_val.append(max(velocities))



        if label not in color_map:
            color = get_random_color_pretty()
            color_map[label] = color

        if label not in map_data_to_labels:
            map_data_to_labels[label] = []

        map_data_to_labels[label].append({'x': evaluation_num, 'y': max_val})
        # x_lists.append(evaluation_num)
        # y_lists.append(max_val)
        # labels.append(label)



    # plot raw data:
    fig = plt.figure(figsize=(10, 12))
    ax = fig.add_subplot(111)
    for label, graphs in map_data_to_labels.items():
        for graph in graphs:
            ax.plot(graph['x'], graph['y'], linewidth=2,
                    label=label, color=color_map[label],
                    markevery=100)
    hnd, lab = get_handles_labels(color_map)
    ax.legend(hnd, lab, loc=0, prop={'size': legend_size})

    ax.tick_params(axis='both', which='major', labelsize=tick_size)
    ax.set_title(args.title, fontsize=title_size, y=1.02)
    xartist = ax.set_xlabel('evaluation #', fontsize=label_size)
    yartist = ax.set_ylabel('fitness', fontsize=label_size)
    ax.grid()
    fig.savefig(out_file_path + ".png", bbox_extra_artists=(xartist, yartist), bbox_inches='tight')
    # ##################################################################################################

    # mean fitness value for the entire label for all generations and all runs:
    overall_means = {}


    # plot averaged data:
    fig = plt.figure(figsize=(10, 12))
    ax = fig.add_subplot(111)
    for label, graphs in map_data_to_labels.items():
        graph_lengths = [len(graph['x']) for graph in graphs]
        mean_y = []

        num_graphs = len(graphs)
        num_points = min(graph_lengths)

        print "for label '{0}'".format(label)
        print "{0} graphs\n{1} points".format(num_graphs, num_points)

        for i in range(num_points):
            sum = 0
            for graph in graphs:
                sum += graph['y'][i]
            sum = sum / float(num_graphs)
            mean_y.append(sum)


        overall_means[float(label)] = mean(mean_y[(num_points/2):])

        ax.plot(graphs[0]['x'][:num_points], mean_y, linewidth=3,
                label=label, color=color_map[label],
                markevery=100)
    hnd, lab = get_handles_labels(color_map)
    ax.legend(hnd, lab, loc=0, prop={'size': legend_size})

    ax.tick_params(axis='both', which='major', labelsize=tick_size)
    ax.set_title(args.title, fontsize=title_size, y=1.02)
    xartist = ax.set_xlabel('evaluation #', fontsize=label_size)
    yartist = ax.set_ylabel('mean fitness', fontsize=label_size)
    ax.grid()
    fig.savefig(out_file_path + "_mean.png", bbox_extra_artists=(xartist, yartist), bbox_inches='tight')
    # ##################################################################################################


    # plot overall means for each label:
    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(111)
    label_values = [float(label) for label in map_data_to_labels]
    label_values = sorted(label_values)
    label_means = [overall_means[label] for label in overall_means]
    ax.scatter(label_values, label_means, label='overall means')
    ax.set_title("overall means", fontsize=title_size, y=1.02)
    xartist = ax.set_xlabel('speciation threshold', fontsize=label_size)
    yartist = ax.set_ylabel('overall mean fitness', fontsize=label_size)
    ax.grid()
    fig.savefig(out_file_path + "_overall_mean.png", bbox_extra_artists=(xartist, yartist), bbox_inches='tight')
    # ##################################################################################################


def get_random_color():
    rand = lambda: random.randint(0, 255)
    return '#%02X%02X%02X' % (rand(), rand(), rand())


def get_random_color_pretty(brightness=0.7):
    N = 30
    cmap = get_colormap(N)
    num = random.choice(range(N))
    color = cmap(num)
    # tone down a bit
    coef = brightness
    color2 = tuple([
        coef*color[0],
        coef*color[1],
        coef*color[2],
        color[3]
    ])
    return color2


def get_handles_labels(label_to_color_map):

    legend_handles = []
    legend_labels = []
    for label in label_to_color_map:
        color = label_to_color_map[label]
        hnd = mlines.Line2D([],[], color=color, linewidth=5)
        legend_handles.append(hnd)
        legend_labels.append(label)
    return legend_handles, legend_labels


def get_colormap(N):
    '''Returns a function that maps each index in 0, 1, ... N-1 to a distinct
    RGB color.'''
    color_norm  = colors.Normalize(vmin=0, vmax=N-1)
    scalar_map = cmx.ScalarMappable(norm=color_norm, cmap='hsv')
    def map_index_to_rgb_color(index):
        return scalar_map.to_rgba(index)
    return map_index_to_rgb_color


if __name__ == '__main__':
    main()
