import yaml
from argparse import ArgumentParser
from matplotlib import pyplot as plt

parser = ArgumentParser("plot_fitness.py")

parser.add_argument('file_path', metavar='PATH', type=str, help="Path to a fitness log file")
parser.add_argument('-t', '--title', type=str, default='plot title', help='Title of the plot')
parser.add_argument('-o', '--output', type=str, default='', help='Output file name')

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

    with open(args.file_path, mode='r') as vel_file:
        yaml_data = vel_file.read()

    data = yaml.load(yaml_data)

    velocities = [(data_item['generation'], data_item['velocities']) for data_item in data]

    velocities = sorted(velocities, key=lambda pair: pair[0])

    generation_num = []
    mean_val = []
    st_dev = []
    med_val = []
    max_val = []
    min_val = []

    for i in range(len(velocities)):
        generation_num.append(velocities[i][0])

        mean_val.append(mean(velocities[i][1]))
        max_val.append(max(velocities[i][1]))
        min_val.append(min(velocities[i][1]))
        med_val.append(median(velocities[i][1]))




        #print(values2)
    plt.figure(figsize=(10,8))
    plt.tick_params(labelsize=20)
    plt.plot(generation_num, mean_val, linewidth=3, label="mean", linestyle = "-",color = 'green', ms=10, markevery=100)
    plt.plot(generation_num, max_val, linewidth=3, label="max", linestyle='--', color = 'red', ms=10, markevery=100)
    plt.plot(generation_num, min_val, linewidth=3, label="min", linestyle='--', color = 'blue', ms=10, markevery=100)
    plt.plot(generation_num, med_val, linewidth=3, label="median", linestyle='--', color = 'black', ms=10, markevery=100)

#   set size of the legend like this: 'size':number
    plt.legend(loc=2, prop={'size':24})

    #plt.plot(values1, values2)
    #plt.plot(values1, values2)
 #   plt.title("5242 nodes, 28980 edges", fontsize=26, y=1.02)
    plt.title(args.title, fontsize=26, y=1.02)
    plt.xlabel('generation #', fontsize=26)
    plt.ylabel('fitness', fontsize=26)
 #   plt.xlim(0, 1800)
    plt.legend(loc=0)
    plt.grid()
    if args.output == '':
        plt.show()
    else:
        plt.savefig(args.output)


if __name__ == '__main__':
    main()