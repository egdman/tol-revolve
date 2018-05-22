import os
import sys
import time
import subprocess

here = os.path.dirname(os.path.abspath(__file__))
tol_path = os.path.abspath(os.path.join(here, '..', '..'))

os.environ['GAZEBO_PLUGIN_PATH'] = os.path.join(tol_path, 'build', 'lib')
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

manager_args = (
' --output-directory test_run'
' --test-bot ../testBots/spiral_diff_coupled'
' --population-size 50'
' --num-children 45'
' --tournament-size 40'
' --evaluation-time 90'
' --warmup-time 3'
' --speciation-threshold 0.05'
' --max-generations 100'
' --repeat-evaluations 1'
' --structural-augmentation-probability 0.8'
' --online'
' --restore-directory restore'
)
print (manager_args)

manager_args = [sys.executable, "gait_learning.py"] + manager_args.split() + sys.argv[1:]

os.chdir(here)
processes['manager'] = subprocess.Popen(manager_args, stdout=subprocess.PIPE)
# self._add_output_stream('manager')

time.sleep(5)



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
