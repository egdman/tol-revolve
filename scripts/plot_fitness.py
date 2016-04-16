import yaml
from argparse import ArgumentParser
from matplotlib import pyplot as plt

parser = ArgumentParser("plot_fitness.py")

parser.add_argument('file_path', metavar='PATH', type=str, help="Path to a fitness log file")
parser.add_argument('-t', '--title', type=str, default='plot title', help='Title of the plot')
parser.add_argument('-o', '--output', type=str, default='', help='Output file name')
parser.add_argument('--all', action='store_true', help='Plot every fitness value')

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

    with open(args.file_path, mode='r') as vel_file:
        yaml_data = vel_file.read()

    data = yaml.load(yaml_data)

    data_items = [(data_item['generation'], data_item['velocities']) for data_item in data]

    data_items = sorted(data_items, key=lambda pair: pair[0])

    generation_num = []
    evaluation_num = []
    mean_val = []
    st_dev = []
    med_val = []
    max_val = []
    min_val = []

    eval_num_all = []
    fit_val_all = []

    for i in range(len(data_items)):

        gen = data_items[i][0]
        velocities = data_items[i][1]

        generation_num.append(gen+1)

        evaluation_num.append((gen+1) * len(velocities))

        mean_val.append(mean(velocities))
        max_val.append(max(velocities))
        min_val.append(min(velocities))
        med_val.append(median(velocities))

        if args.all:
            eval_num_all.extend([num for num in range
                (
                    len(velocities)*(gen),
                    len(velocities)*(gen+1)
                )
            ])
            fit_val_all.extend(reversed(velocities))





        #print(values2)
    fig = plt.figure(figsize=(10,8))
    ax = fig.add_subplot(111)
    ax.plot(evaluation_num, max_val, linewidth=3, label="max", linestyle='--', color = 'red', ms=10, markevery=100)
    ax.plot(evaluation_num, mean_val, linewidth=3, label="mean", linestyle = "-",color = 'green', ms=10, markevery=100)
    ax.plot(evaluation_num, med_val, linewidth=3, label="median", linestyle=':', color = 'black', ms=10, markevery=100)
    ax.plot(evaluation_num, min_val, linewidth=3, label="min", linestyle='--', color = 'blue', ms=10, markevery=100)

    if args.all:
        ax.plot(eval_num_all, fit_val_all, linewidth=1, label="all", alpha=0.3)

#   set size of the legend like this: 'size':number
    ax.legend(loc=0, prop={'size': legend_size})

    ax.tick_params(axis='both', which='major', labelsize=tick_size)
    ax.set_title(args.title, fontsize=title_size, y=1.02)
    xartist = ax.set_xlabel('evaluation #', fontsize=label_size)
    yartist = ax.set_ylabel('fitness', fontsize=label_size)

    ax.grid()
    if args.output == '':
        plt.show()
    else:
        fig.savefig(args.output, bbox_extra_artists=(xartist,yartist), bbox_inches='tight')


if __name__ == '__main__':
    main()
