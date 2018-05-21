#ifndef REVOLVE_GAZEBO_SENSORS_DIRECTION_SENSOR_H_
#define REVOLVE_GAZEBO_SENSORS_DIRECTION_SENSOR_H_

#include "Sensor.h"
#include "DirectionSensorDummy.h"

#include <gazebo/msgs/msgs.hh>
#include <boost/shared_ptr.hpp>

namespace revolve {
namespace gazebo {
	

class DirectionSensor : public Sensor
{
public:
	DirectionSensor(::gazebo::physics::ModelPtr model, sdf::ElementPtr sensor,
			std::string partId, std::string sensorId);
			
	virtual ~DirectionSensor();
	
	/**
	 * Read the value of this sensor into the
	 * input address.
	 */
	virtual void read(double * input);

	/**
	 * Called when the sound sensor is updated
	 */
	void OnUpdate(::gazebo::sensors::SensorPtr);


	/**
	 * Called when the drive direction is updated
	 */
	void OnDirUpdate(const boost::shared_ptr<::gazebo::msgs::Vector3d const> &_msg);
	

protected:

	// Drive direction vector
	::gazebo::math::Vector3 driveDirection_;

	// Transport node
	::gazebo::transport::NodePtr node_;
	
    // Subscriber to SoundPlugin messages:
    ::gazebo::transport::SubscriberPtr soundPluginSub_;

	// Pointer to the update connection
	::gazebo::event::ConnectionPtr updateConnection_;

    // Relative pose of this sensor in the coordinate system of the parent link
    ::gazebo::math::Pose sensorPose_;

    // The sensor axis in the parent link coordinate system
    ::gazebo::math::Vector3 sensorAxis_;

    // Pointer to the parent link
    ::gazebo::physics::LinkPtr linkPtr_;

    // Calculate output value based on the orientation of the sensor and the drive direction
    virtual void calculateOutput();

private:
	double output_;
};
} // namespace gazebo
} // namespace revolve
	


#endif // REVOLVE_GAZEBO_SENSORS_DIRECTION_SENSOR_H_
