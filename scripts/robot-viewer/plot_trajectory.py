from argparse import ArgumentParser
from matplotlib import pyplot as plt

parser = ArgumentParser("plot_trajectory.py")

parser.add_argument('file_path', metavar='PATH', type=str, help="Path to a trajectory file")
parser.add_argument('-t', '--title', type=str, default='plot title', help='Title of the plot')
parser.add_argument('-o', '--output', type=str, default='', help='Output file name')


def main():
    args = parser.parse_args()

    times = []
    xs = []
    ys = []

    with open(args.file_path, mode='r') as traj_file:
        for line in traj_file:
            values = line.split(',')
            try:
                time = float(values[0])
                x = float(values[1])
                y = float(values[2])
                z = float(values[3])
                xs.append(x*100)
                ys.append(y*100)
            except:
                pass


    plt.figure(figsize=(10,8))
    plt.axes().set_aspect('equal', 'datalim')

    plt.tick_params(labelsize=20)
    plt.plot(xs, ys, linewidth=3, label="trajectory", linestyle = "-",color = 'green', ms=10, markevery=100)

#   set size of the legend like this: 'size':number
    plt.legend(loc=0, prop={'size':20})

    #plt.plot(values1, values2)
    #plt.plot(values1, values2)nn
 #   plt.title("5242 nodes, 28980 edges", fontsize=26, y=1.02)
    plt.title(args.title, fontsize=26, y=1.02)
    plt.xlabel('x, cm', fontsize=26)
    plt.ylabel('y, cm', fontsize=26)
    # plt.xlim(-50, 50)
    # plt.ylim(-50, 50)
#    plt.legend(loc=0)
    plt.grid()
    if args.output == '':
        plt.show()
    else:
        plt.savefig(args.output)


if __name__ == '__main__':
    main()
