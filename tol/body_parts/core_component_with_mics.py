# System imports
from __future__ import absolute_import

# SDF builder imports
from sdfbuilder.sensor import Sensor as SdfSensor
from sdfbuilder import Pose
from sdfbuilder.math import Vector3, Quaternion
from sdfbuilder.structure import Box, Mesh

# Revolve imports
from revolve.build.sdf import BodyPart
from revolve.build.util import in_grams, in_mm

# Local imports
from .util import ColorMixin
from .core_component import CoreComponent, WIDTH


class CoreComponentWithMics(CoreComponent):
    """
    The core component of the robot, basically a box with an IMU sensor.
    """

    def _initialize(self, **kwargs):
        """
        :param kwargs:
        :return:
        """

        super(CoreComponentWithMics, self)._initialize(**kwargs)

        half_width = WIDTH / 2.0
        right_angle = 3.14159265/2.0

        # rotates clockwise around axis by angle:
        mic_pose_1 = Pose(
            position=Vector3(0, half_width, 0),
            rotation=Quaternion.from_angle_axis(angle=right_angle, axis=Vector3(-1,0,0))
        )

        mic_pose_2 = Pose(
            position=Vector3(half_width, 0, 0),
            rotation=Quaternion.from_angle_axis(angle=right_angle, axis=Vector3(0,1,0))
        )

        mic_pose_3 = Pose(
            position=Vector3(0, -half_width, 0),
            rotation=Quaternion.from_angle_axis(angle=right_angle, axis=Vector3(1,0,0))
        )

        mic_pose_4 = Pose(
            position=Vector3(-half_width, 0, 0),
            rotation=Quaternion.from_angle_axis(angle=right_angle, axis=Vector3(0,-1,0))
        )

        # The second argument ("direction") is the type of the sensor that is checked in SensorFactory.cpp.
        # Any existing type of gazebo sensors can be used. Beside that, a new type can be registered in WorldController.cpp
        mic_1 = SdfSensor("dir_sensor_1", "direction", pose=mic_pose_1, update_rate=self.conf.sensor_update_rate)
        mic_2 = SdfSensor("dir_sensor_2", "direction", pose=mic_pose_2, update_rate=self.conf.sensor_update_rate)
        mic_3 = SdfSensor("dir_sensor_3", "direction", pose=mic_pose_3, update_rate=self.conf.sensor_update_rate)
        mic_4 = SdfSensor("dir_sensor_4", "direction", pose=mic_pose_4, update_rate=self.conf.sensor_update_rate)

        self.link.add_sensor(mic_1)
        self.link.add_sensor(mic_2)
        self.link.add_sensor(mic_3)
        self.link.add_sensor(mic_4)