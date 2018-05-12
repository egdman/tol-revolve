# Global / system
import uuid
from pygazebo.msg import world_control_pb2

# Revolve
from .connect import connect, RequestHandler
from .analyze import BodyAnalyzer
from ...logging import logger

# Construct a unique message base
MSG_BASE = uuid.uuid4().int


class WorldManager(object):
    """
    Class for basic world management such as inserting / deleting
    models
    """

    def __init__(self, world_address=None):
        self.world_address = world_address
        self.manager = None
        self.world_control = None


    @classmethod
    async def create(cls, world_address=("127.0.0.1", 11345)):
        self = cls(world_address=world_address)
        await self._init()
        return self


    async def _init(self):
        """
        Initializes connections for the world manager
        :return:
        """
        if self.manager is not None:
            return

        # Initialize the manager / analyzer connections as well as
        # the general request handler
        self.manager = await connect(self.world_address)

        self.world_control = await self.manager.advertise(
            '/gazebo/default/world_control', 'gazebo.msgs.WorldControl')

        self.request_handler = await RequestHandler.create(
            self.manager, msg_id_base=MSG_BASE)

        # Wait for connections
        await self.world_control.wait_for_listener()


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


    async def insert_model(self, sdf):
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
        return await self.request_handler.do_gazebo_request("insert_sdf", data=str(sdf))


    async def delete_model(self, name, req="entity_delete"):
        """
        Deletes the model with the given name from the world.
        :param name:
        :param req: Type of request to use. If you are going to
        delete a robot, I suggest using `delete_robot` rather than `entity_delete`
        because this attempts to prevent some issues with segmentation faults
        occurring from deleting sensors.
        :return:
        """
        return await self.request_handler.do_gazebo_request(req, data=name)
