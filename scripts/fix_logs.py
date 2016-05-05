import os
import fnmatch
import yaml
from argparse import ArgumentParser


parser = ArgumentParser()

parser.add_argument('dir_path', metavar='PATH', type=str, help="Path to a genotype log directory")
parser.add_argument('-p', '--pattern', type=str, default='genotypes.log', help="Pattern to match filenames")
parser.add_argument('-o', '--output-dir', type=str, default='', help='Output directory')



def main():
    args = parser.parse_args()

    dir_path = args.dir_path
    out_dir_path = args.output_dir

    if out_dir_path == '':
        out_dir_path = os.path.join(dir_path, "fixed")

    try:
        os.mkdir(out_dir_path)
    except OSError:
        pass


    files_and_dirs = os.listdir(dir_path)
    files = [f for f in files_and_dirs if os.path.isfile(os.path.join(dir_path, f)) and
             fnmatch.fnmatch(f, args.pattern)]

    for filename in files:
        with open(os.path.join(dir_path, filename), mode='r') as brain_file:
            print "input: {0}".format(filename)
            out_string = ""

            base_level = 0
            for line in brain_file:
                out_line = line

                if "generation" in line and "- generation" not in line:
                    base_level = 1
                    # replace 'generation #0 with '- generation : 0'
                    out_line = "- {0}".format(line)
                    out_line = out_line.replace(' #', ' : ')
                    level = base_level - 1
                elif "velocity" in line and "- velocity" not in line:
                    # replace 'velocity' with '- velocity'
                    out_line = "- {0}".format(line)
                    level = base_level
                elif "- velocity" in line:
                    level = base_level
                else:
                    level = base_level + 1

                for l in range(level):
                    out_line = "  {0}".format(out_line)

                out_string += out_line
            print base_level
            with open(os.path.join(out_dir_path, filename), mode='w') as out_file:
                out_file.write(out_string)


if __name__ == '__main__':
    main()
