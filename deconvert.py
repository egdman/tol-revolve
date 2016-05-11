import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from revolve.convert import yaml_to_robot, robot_to_yaml

from tol.spec import get_body_spec, get_brain_spec
from tol.config import parser

parser.add_argument( 'file_name', metavar='FILENAME', type=str, help='path to input YAML file')
parser.add_argument('-o', '--output', type=str, default='output.yaml', help='name of the output file')

def main():
    conf = parser.parse_args()

    in_path = conf.file_name
    out_path = os.path.join(os.path.dirname(in_path), conf.output)

    with open(in_path,'r') as yamlfile:
        yaml_bot = yamlfile.read()

    body_spec = get_body_spec(conf)
    brain_spec = get_brain_spec(conf)

    print "converting to protobuf..."
    pb_bot = yaml_to_robot(body_spec, brain_spec, yaml_bot)

    print "converting to yaml..."
    yaml_bot = robot_to_yaml(body_spec, brain_spec, pb_bot)

    with open(out_path,'w') as out_file:
        out_file.write(yaml_bot)

    print "done"



if __name__ == '__main__':
    main()
