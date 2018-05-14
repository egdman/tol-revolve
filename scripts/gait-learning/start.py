import os
import sys
import time
import subprocess


here = os.path.dirname(os.path.abspath(__file__))
tol_path = os.path.abspath(os.path.join(here, '..', '..'))
# rv_path = os.path.abspath(os.path.join(tol_path, '..', 'revolve'))

# args = parser.parse_args()

os.environ['GAZEBO_PLUGIN_PATH'] = os.path.join(tol_path, 'build')
os.environ['GAZEBO_MODEL_PATH'] = os.path.join(tol_path, 'tools', 'models')
world_file = os.path.join(here, 'gait-learning.world')

processes = {}

def _launch_with_ready_str(commands, ready_str):
    """
    :param cmd:
    :param ready_str:
    :return:
    """
    proc = subprocess.Popen(commands, stdout=subprocess.PIPE)

    ready = False
    while True:
        out = proc.stdout.readline().decode(encoding='utf-8')
        sys.stdout.write(out)
        if ready_str in out: break
        time.sleep(0.1)
    return proc


gazebo_ready = "World plugin loaded"






def terminate_process(proc):
    process = psutil.Process(proc.pid)
    for child in process.children(recursive=True):
        child.terminate()

    process.terminate()



print("Launching Gazebo...")

gazebo_cmd = ["gzserver", "-u", world_file]
processes["gazebo"] = _launch_with_ready_str(gazebo_cmd, gazebo_ready)




print("Launching experiment manager...")

manager_args = [sys.executable, "gait_learning.py"] + sys.argv[1:]
processes['manager'] = subprocess.Popen(manager_args, stdout=subprocess.PIPE)
# self._add_output_stream('manager')





for _, process in processes.items():
	process.terminate()

print ("DONE!!!!!!")
# supervisor = Supervisor(
#     manager_cmd=[sys.executable, "gait_learning.py"],
#     analyzer_cmd=os.path.join(rv_path, 'tools', 'analyzer', 'run-analyzer'),
#     world_file=os.path.join(here, 'gait-learning.world'),
#     output_directory=args.output_directory,
#     manager_args=sys.argv[1:],
#     restore_directory=args.restore_directory,
#     gazebo_cmd="gzserver"
# )

# supervisor.launch()
