import pygazebo
from pygazebo.msg import request_pb2, response_pb2

# Default connection address to keep things DRY. This is an array
# rather than a tuple, so it is writeable as long as you change
# the separate elements.
default_address = ["127.0.0.1", 11345]


async def connect(address=default_address):
    return await pygazebo.connect(address=tuple(address))


class MessagePublisher(object):

    @classmethod
    async def create(cls, manager, topic, msg_type):
        self = cls()
        self.publisher await manager.advertise(
            topic,
            msg_type)

        await self.publisher.wait_for_listener()
        return self

   
    async def publish(self, msg):
        yield From(self.publisher.publish(msg))


class RequestHandler(object):
    """
    Utility class to send `Request` messages and accept
    responses to them.
    """
    # Object used to make constructor private

    def __init__(self, manager, request_class, request_type,
                 response_class, response_type,
                 advertise, subscribe, id_attr, request_attr, msg_id_base):
        """
        Private constructor, use the `create` coroutine instead.
        :param manager:
        :return:
        """
        self.id_attr = id_attr
        self.request_attr = request_attr
        self.response_type = response_type
        self.request_type = request_type
        self.request_class = request_class
        self.subscribe = subscribe
        self.advertise = advertise
        self.response_class = response_class
        self.manager = manager
        self.pending_requests = {}
        self.publisher = None
        self.msg_id = int(msg_id_base)

    @classmethod
    async def create(cls, manager,
               request_class=request_pb2.Request,
               request_type='gazebo.msgs.Request',
               response_class=response_pb2.Response,
               response_type='gazebo.msgs.Response',
               advertise='/gazebo/default/request',
               subscribe='/gazebo/default/response',
               id_attr='id',
               request_attr='request',
               msg_id_base=0):
        """

        :param manager:
        :param request_class:
        :param request_type:
        :param response_class:
        :param response_type:
        :param advertise:
        :param subscribe:
        :param id_attr:
        :param msg_id_base:
        :return:
        """
        handler = cls(manager, request_class, request_type, response_class, response_type,
                      advertise, subscribe, id_attr, request_attr, msg_id_base)
        await handler._init()
        return handler

    
    async def _init(self):
        """
        :return:
        """
        if self.publisher is not None:
            return

        self.subscriber = self.manager.subscribe(
            self.subscribe,
            self.response_type,
            self._callback)

        self.publisher = await self.manager.advertise(
            self.advertise,
            self.request_type)

        await self.subscriber.wait_for_connection()
        await self.publisher.wait_for_listener()


    def _callback(self, data):
        """
        :param data:
        :return:
        """
        msg = self.response_class()
        msg.ParseFromString(data)

        msg_id = str(self.get_id_from_msg(msg))
        request_type = str(self.get_request_type_from_msg(msg))

        # Call the future's set_result
        self.pending_requests[msg_id].set_result(msg)
        del self.pending_requests[msg_id]


    def get_id_from_msg(self, msg):
        """
        Returns the ID given a protobuf message.
        :param msg:
        :return:
        """
        return getattr(msg, self.id_attr)

    def get_request_type_from_msg(self, msg):
        """
        Returns the request type from a protobuf message.
        :param msg:
        :return:
        """
        return getattr(msg, self.request_attr)


    def get_new_msg_id(self):
        """
        Message ID sequencer.
        :return:
        """
        self.msg_id += 1
        return self.msg_id

    
    def do_gazebo_request(self, request, data=None, dbl_data=None, msg_id=None):
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
        if msg_id is None:
            msg_id = self.get_new_msg_id()

        req = request_pb2.Request()
        req.id = msg_id
        req.request = request

        if data is not None:
            req.data = data

        if dbl_data is not None:
            req.dbl_data = dbl_data

        return await self.do_request(req)


    async def do_request(self, msg):
        """
        Performs a request. The only requirement
        of `msg` is that it has an `id` attribute.

        Publishing of the request is always yielded to prevent multiple messages
        from going over the same pipe. The returned future is for the response.

        :param msg: Message object to publish
        :return:
        """
        msg_id = str(self.get_id_from_msg(msg))
        request_type = str(self.get_request_type_from_msg(msg))

        if msg_id in self.pending_requests:
            raise RuntimeError("Duplicate request ID: {} of type {}".format(msg_id, request_type))

        future = asyncio.Future()
        self.pending_requests[msg_id] = future
        await self.publisher.publish(msg)
        return future