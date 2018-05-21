from subprocess import check_output
import os
import re
import fnmatch

gazebo_info = check_output('pkg-config gazebo --cflags', shell=True)

hit = re.search(r'-I(\S*gazebo\S*).*', gazebo_info)
if not hit:
    sys.exit("Gazebo is not installed")

gazebo_include_dir =  hit.group(1)
gazebo_proto_dir = os.path.join(gazebo_include_dir, "gazebo", "msgs", "proto")

package_dir = 'spec'
proto_dir = 'spec/msgs'

# generate protobuf python files
check_output(
    'protoc -I {GAZEBO_INCLUDE_DIR} -I {GAZEBO_PROTO_DIR} -I spec --python_out={PKG_DIR}/ {PROTO_DIR}/*.proto'
    .format(
        GAZEBO_INCLUDE_DIR = gazebo_include_dir,
        GAZEBO_PROTO_DIR = gazebo_proto_dir,
        PKG_DIR = package_dir,
        PROTO_DIR = proto_dir),
    shell=True)


# fix bullshit include syntax in protobuf-generated python files
generated_files = (f for f in check_output("ls spec/msgs", shell=True).split() if fnmatch.fnmatch(f, "*_pb2.py"))

# all imports not containing msgs. and ending with _pb2 are assumed to be from pygazebo.msg
gazebo_package_finder = re.compile(r'^import\s+((?!msgs\.).*_pb2)', re.MULTILINE)
replace_with = r'from pygazebo.msg import \1'

for fname in generated_files:
    fpath = os.path.join(proto_dir, fname)
    with open(fpath, 'r') as stream:
        text = stream.read()

    text = re.sub(gazebo_package_finder, replace_with, text)
    with open(fpath, 'w') as stream:
        stream.write(text)
