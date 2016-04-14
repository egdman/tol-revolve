import os
from argparse import ArgumentParser
from matplotlib import pyplot as plt

parser = ArgumentParser("plot_trajectory.py")

parser.add_argument('dir_path', metavar='PATH', type=str, help="Path to a trajectory directory")
parser.add_argument('-t', '--title', type=str, default='plot title', help='Title of the plot')
parser.add_argument('-o', '--output', type=str, default='', help='Output file name')


def main():
    args = parser.parse_args()

    plt.figure(figsize=(10, 8))
    plt.axes().set_aspect('equal', 'datalim')
    plt.tick_params(labelsize=20)
    plt.title(args.title, fontsize=26, y=1.02)
    plt.xlabel('x, cm', fontsize=26)
    plt.ylabel('y, cm', fontsize=26)
    plt.grid()



    dir_path = args.dir_path
    files_and_dirs = os.listdir(dir_path)
    files = [f for f in files_and_dirs if os.path.isfile(os.path.join(dir_path, f))]

    for filename in files:
        filepath = os.path.join(dir_path, filename)
        times = []
        xs = []
        ys = []

        with open(filepath, mode='r') as traj_file:
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


        plt.plot(xs, ys, linewidth=3, linestyle = "-",color = 'green', ms=10, markevery=100)


    if args.output == '':
        plt.show()
    else:
        plt.savefig(args.output)


if __name__ == '__main__':
    main()
