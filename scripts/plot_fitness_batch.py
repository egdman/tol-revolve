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
parser.add_argument('-o', '--output', type=str, default='plot.png', help='Output file name')

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

    dir_path = args.dir_path
    out_file_path = os.path.join(dir_path, args.output)

    files_and_dirs = os.listdir(dir_path)
    files = [f for f in files_and_dirs if os.path.isfile(os.path.join(dir_path, f))]

    labels = []
    x_lists = []
    y_lists = []

    color_map = {} # dictionary {label:color} because we want the same labels have the same color

    # plt.register_cmap('inferno', cmap=colors.inferno)

    for filename in files:
        file_path = os .path.join(dir_path, filename)
        print "input :  {0}".format(file_path)

        with open(file_path, 'r') as in_file:
            yaml_data = in_file.read()

        label = filename.split('-')[-2]
        print 'label : {0}'.format(label)

 #       color = get_random_color()
        color = get_random_color_pretty()

        color_map[label] = color

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

        x_lists.append(evaluation_num)
        y_lists.append(max_val)
        labels.append(label)


    plt.figure(figsize=(10,8))
    plt.tick_params(labelsize=20)
    for i in range(len(labels)):
        plt.plot(x_lists[i], y_lists[i], linewidth=3, label=labels[i], color=color_map[labels[i]], ms=10, markevery=100)

    hnd, lab = get_handles_labels(color_map)

    plt.legend(hnd, lab, loc=0, prop={'size': 20})

    plt.title(args.title, fontsize=26, y=1.02)
    plt.xlabel('evaluation #', fontsize=26)
    plt.ylabel('fitness', fontsize=26)
# #    plt.xlim(100, None)
# #    plt.legend(loc=0)

    plt.grid()
    plt.savefig(out_file_path)


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
        legend_labels.append("population of {0}".format(label))
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
