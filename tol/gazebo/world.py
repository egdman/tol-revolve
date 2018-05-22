# Global / system
import os
import csv
import uuid
import asyncio

from pygazebo.msg import world_control_pb2, request_pb2, poses_stamped_pb2, gz_string_pb2
from sdfbuilder.math import Vector3

from .robot import Robot

from ..revolve.msgs.model_inserted_pb2 import ModelInserted
from ..revolve.util import Time

from .connect import connect, RequestHandler
from ..logging import logger


class WorldManager(object):
    """
    A WorldManager utility class with methods more suited to
    Revolve.Angle, such as inserting whole robot trees etc.
    """

    def __init__(self, world_address=None, analyzer_address=None,
                 output_directory=None, pose_update_frequency=None,
                 restore=None):
        """

        :param restore: Restore the world from this directory, if available. Only works
                         if `output_directory` is also specified.
        :param pose_update_frequency:
        :param generator:
        :param _private:
        :param world_address:
        :param analyzer_address:
        :param builder:
        :param output_directory:
        :return:
        """

        self.world_address = world_address
        self.connection = None
        self.world_control = None
        self.unique_id = uuid.uuid4().time_mid

        # Output files for robot CSV data
        self.robots_file = None
        self.poses_file = None
        # self.write_robots = None
        # self.write_poses = None
        self.output_directory = None
        self.robots_filename = None
        self.poses_filename = None
        self.snapshot_filename = None
        self.world_snapshot_filename = None

        self.pose_update_frequency = pose_update_frequency

        self.robots = {}
        self.robot_id = 0

        self.start_time = None
        self.last_time = None

        # List of functions called when the local state updates
        self.update_triggers = []

        self.do_restore = None

        if output_directory:
            if not restore:
                restore = datetime.now().strftime(datetime.now().strftime('%Y%m%d%H%M%S'))

            self.output_directory = os.path.join(output_directory, restore)

            if not os.path.exists(self.output_directory):
                os.mkdir(self.output_directory)

            self.snapshot_filename = os.path.join(self.output_directory, 'snapshot.pickle')
            if os.path.exists(self.snapshot_filename):
                # Snapshot exists - restore from it
                with open(self.snapshot_filename, 'rb') as snapshot_file:
                    self.do_restore = pickle.load(snapshot_file)

            self.world_snapshot_filename = os.path.join(self.output_directory, 'snapshot.world')

            self.robots_filename = os.path.join(self.output_directory, 'robots.csv')
            self.poses_filename = os.path.join(self.output_directory, 'poses.csv')

            if self.do_restore:
                # Copy snapshot files and open created files in append mode
                # TODO Delete robot sdf / pb files that were created after the snapshot
                shutil.copy(self.poses_filename+'.snapshot', self.poses_filename)
                shutil.copy(self.robots_filename+'.snapshot', self.robots_filename)

                self.robots_file = open(self.robots_filename, 'ab')
                self.poses_file = open(self.poses_filename, 'ab')
                # self.write_robots = csv.writer(self.robots_file, delimiter=',')
                # self.write_poses = csv.writer(self.poses_file, delimiter=',')
            else:
                # Open poses file, this is written *a lot* so use default OS buffering
                self.poses_file = open(os.path.join(self.output_directory, 'poses.csv'), 'wb')

                # Open robots file line buffered so we can see it on the fly, isn't written
                # too often.
                self.robots_file = open(os.path.join(self.output_directory, 'robots.csv'), 'wb', buffering=1)
                # self.write_robots = csv.writer(self.robots_file, delimiter=',')
                # self.write_poses = csv.writer(self.poses_file, delimiter=',')

                # self.write_robots.writerow(self.robots_header())
                # self.write_poses.writerow(self.poses_header())




    # async def create(cls, world_address=("127.0.0.1", 11345), pose_update_frequency=10):
    #     self = cls(world_address=world_address, pose_update_frequency=pose_update_frequency)
    #     await self._init()
    #     return self



    async def _init(self):
        """
        Initializes connections for the world manager
        :return:
        """
        if self.connection is not None:
            return

        # Initialize the manager / analyzer connections as well as
        # the general request handler
        self.connection = await connect(self.world_address)

        self.world_control = await self.connection.advertise(
            '/gazebo/default/world_control', 'gazebo.msgs.WorldControl')

        # Wait for connections
        await self.world_control.wait_for_listener()

        # Subscribe to pose updates
        self.pose_subscriber = self.connection.subscribe(
            '/gazebo/default/revolve/robot_poses',
            'gazebo.msgs.PosesStamped',
            self._update_poses)

        # Wait for connections
        await self.pose_subscriber.wait_for_connection()

        self.request_handler = await RequestHandler.create(self.connection)

        await self.set_pose_update_frequency(self.pose_update_frequency)

        if self.do_restore:
            self.restore_snapshot(self.do_restore)



    async def pause(self, pause):
        """
        Pause / unpause the world
        :param pause:
        :return: Future for the published message
        """
        if pause:
            logger.debug("Pausing the world.")
        else:
            logger.debug("Unpausing the world.")

        msg = world_control_pb2.WorldControl()
        msg.pause = pause
        return await self.world_control.publish(msg)


    def insert_model(self, sdf):
        """
        Insert a model wrapped in an SDF tag into the world. Make
        sure it has a unique name, as it will be literally inserted into the world.

        This coroutine yields until the request has been successfully sent.
        It returns a future that resolves when a response has been received. The
        optional given callback is added to this future.

        :param sdf:
        :type sdf: SDF
        :return:
        """
        return self._do_gazebo_request("insert_sdf", data=str(sdf))


    def delete_model(self, name, req="entity_delete"):
        """
        Deletes the model with the given name from the world.
        :param name:
        :param req: Type of request to use. If you are going to
        delete a robot, I suggest using `delete_robot` rather than `entity_delete`
        because this attempts to prevent some issues with segmentation faults
        occurring from deleting sensors.
        :return:
        """
        return self._do_gazebo_request(req, data=name)



    def get_unique_id(self):
        self.unique_id += 1
        return self.unique_id


    def robots_header(self):
        """
        Returns the header to be written to the robots file
        :return:
        """
        return ['id', 'parent1', 'parent2']


    def poses_header(self):
        """
        Returns the header to be written to the poses file
        :return:
        """
        return ['id', 'sec', 'nsec', 'x', 'y', 'z']



    def teardown(self):
        """
        Finalizes the world, flushes files, etc.
        :return:
        """
        if self.robots_file:
            self.robots_file.close()
            self.poses_file.close()



    async def create_snapshot(self):
        """
        Creates a snapshot of the world in the output directory. This pauses the world.
        :return:
        """
        if not self.output_directory:
            logger.warning("No output directory - no snapshot will be created.")
            return False

        # Pause the world
        await self.pause(True)

        # Obtain a copy of the current world SDF from Gazebo and write it to file
        response = await self._do_gazebo_request("world_sdf")
        if response.response == "error":
            logger.warning("WARNING: requesting world state resulted in error. Snapshot failed.")
            return False

        msg = gz_string_pb2.GzString()
        msg.ParseFromString(response.serialized_data)
        with open(self.world_snapshot_filename, 'wb') as f:
            f.write(msg.data)

        # Get the snapshot data and pickle to file
        data = self.get_snapshot_data()

        with open(self.snapshot_filename, 'wb') as f:
            pickle.dump(data, f)

        # Flush statistic files and copy them
        self.poses_file.flush()
        self.robots_file.flush()
        shutil.copy(self.poses_filename, self.poses_filename+'.snapshot')
        shutil.copy(self.robots_filename, self.robots_filename+'.snapshot')
        return True



    def restore_snapshot(self, data):
        """
        Called with the data object created and pickled in `get_snapshot_data`,
        should restore the state of the world manager to where
        it can continue the way it left off.
        :param data:
        :return:
        """
        self.robots = data['robots']
        self.robot_id = data['robot_id']
        self.start_time = data['start_time']
        self.last_time = data['last_time']



    def get_snapshot_data(self):
        """
        Returns a data object to be pickled into a snapshot file.
        This should contain
        :return:
        """
        return {
            "robots": self.robots,
            "robot_id": self.robot_id,
            "start_time": self.start_time,
            "last_time": self.last_time
        }


    def _do_gazebo_request(self, request, data=None, dbl_data=None):
        """
        Convenience wrapper to use `do_request` with a default Gazebo
        `Request` message. See that method for more info.

        :param request:
        :type request: str
        :param data:
        :param dbl_data:
        :param msg_id: Force the message to use this ID. Sequencer is used if no message
                       ID is specified.
        :type msg_id: int
        :return:
        """
        req = request_pb2.Request()
        req.id = self.get_unique_id()
        req.request = request

        if data is not None:
            req.data = data

        if dbl_data is not None:
            req.dbl_data = dbl_data

        return self.request_handler.do_request(req)



    def set_pose_update_frequency(self, freq):
        """
        Sets the pose update frequency. Defaults to 10 times per second.
        :param freq:
        :type freq: int
        :return:
        """
        self.pose_update_frequency = freq
        return self._do_gazebo_request("set_robot_pose_update_frequency", str(freq))


    def get_robot_id(self):
        """
        Robot ID sequencer
        :return:
        """
        self.robot_id += 1
        return self.robot_id

    def robot_list(self):
        """
        Returns the list of registered robots
        :return:
        :rtype: list[Robot]
        """
        return self.robots.values()

    def get_robot_by_name(self, name):
        """
        :param name:
        :return:
        :rtype: Robot|None
        """
        return self.robots.get(name, None)


    def insert_robot(self, tree, pose, parents=None):
        """
        Inserts a robot into the world. This consists of two steps:

        - Sending the insert request message
        - Receiving a ModelInfo response

        This method is a coroutine because of the first step, writing
        the message must be yielded since PyGazebo doesn't appear to
        support writing multiple messages simultaneously. For the response,
        i.e. the message that confirms the robot has been inserted, a
        future is returned.

        :param parents:
        :param tree:
        :type tree: Tree
        :param pose:
        :type pose: Pose
        :return: A future that resolves with the created `Robot` object.
        """
        robot_id = self.get_robot_id()
        robot_name = "gen__" + str(robot_id)

        robot = tree.to_robot(robot_id)
        sdf = self.get_simulation_sdf(robot, robot_name)
        sdf.elements[0].set_pose(pose)

        if self.output_directory:
            with open(os.path.join(self.output_directory, 'robot_%d.sdf' % robot_id), 'w') as f:
                f.write(str(sdf))

        return_future = asyncio.Future()
        insert_future = self.insert_model(sdf)
        insert_future.add_done_callback(lambda fut: self._robot_inserted(
            robot_name, tree, robot, parents, fut.result(), return_future))

        asyncio.ensure_future(insert_future)
        return return_future


    def get_simulation_sdf(self, robot, robot_name):
        """

        :param robot:
        :type robot: PbRobot
        :param robot_name:
        :return:
        :rtype: SDF
        """
        raise NotImplementedError("Implement in subclass if you want to use this method.")


    def delete_robot(self, robot):
        """
        :param robot:
        :type robot: Robot
        :return:
        """
        # Immediately unregister the robot so no it won't be used
        # for anything else while it is being deleted.
        self.unregister_robot(robot)
        return self.delete_model(robot.name, req="delete_robot")


    def _robot_inserted(self, robot_name, tree, robot, parents, msg, return_future):
        """
        Registers a newly inserted robot and marks the insertion
        message response as handled.

        :param tree:
        :param robot_name:
        :param tree:
        :param robot:
        :param parents:
        :param msg:
        :type msg: pygazebo.msgs.response_pb2.Response
        :param return_future: Future to resolve with the created robot object.
        :type return_future: Future
        :return:
        """
        inserted = ModelInserted()
        inserted.ParseFromString(msg.serialized_data)
        model = inserted.model
        time = Time(msg=inserted.time)
        p = model.pose.position
        position = Vector3(p.x, p.y, p.z)

        robot = Robot(robot_name, tree, robot, position, time, parents)
        self.register_robot(robot)
        return_future.set_result(robot)



    def register_robot(self, robot):
        """
        Registers a robot with its Gazebo ID in the local array.
        :param robot:
        :type robot: Robot
        :return:
        """
        logger.debug("Registering robot %s." % robot.name)

        if robot.name in self.robots:
            raise ValueError("Duplicate robot: %s" % robot.name)

        self.robots[robot.name] = robot
        # if self.output_directory:
        #     # Write robot details and CSV row to files
        #     robot.write_robot('%s/robot_%d.pb' % (self.output_directory, robot.robot.id),
        #                       self.write_robots)


    def unregister_robot(self, robot):
        """
        Unregisters the robot with the given ID, usually happens when
        it is deleted.
        :param robot:
        :type robot: Robot
        :return:
        """
        logger.debug("Unregistering robot %s." % robot.name)
        del self.robots[robot.name]


    def _update_poses(self, msg):
        """
        Handles the pose info message by updating robot positions.
        :param msg:
        :return:
        """
        poses = poses_stamped_pb2.PosesStamped()
        poses.ParseFromString(msg)

        self.last_time = t = Time(msg=poses.time)
        if self.start_time is None:
            self.start_time = t

        for pose in poses.pose:
            robot = self.robots.get(pose.name, None)
            if not robot:
                continue

            position = Vector3(pose.position.x, pose.position.y, pose.position.z)
            # robot.update_position(t, position, self.write_poses)

        self.call_update_triggers()


    def add_update_trigger(self, callback):
        """
        Adds an update trigger, a function called every time the local
        state is updated.
        :param callback:
        :type callback: callable
        :return:
        """
        self.update_triggers.append(callback)

    def remove_update_trigger(self, callback):
        """
        Removes a previously installed update trigger.
        :param callback:
        :type callback: callable
        :return:
        """
        self.update_triggers.remove(callback)

    def call_update_triggers(self):
        """
        Calls all update triggers.
        :return:
        """
        for callback in self.update_triggers:
            callback(self)
