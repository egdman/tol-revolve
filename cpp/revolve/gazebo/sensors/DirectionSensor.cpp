#include "DirectionSensor.h"

#include <iostream>
#include <stdexcept>


namespace gz = gazebo;

namespace revolve {
namespace gazebo {
	
DirectionSensor::DirectionSensor(::gazebo::physics::ModelPtr model, sdf::ElementPtr sensor,
		std::string partId, std::string sensorId):
        Sensor(model, sensor, partId, sensorId, 1) // last parameter is the number of input neurons this sensor generates
		
{

    this->sensor_ = boost::dynamic_pointer_cast<::gz::sensors::DirectionSensorDummy>(this->sensor_);
    if (!this->sensor_)
    {
        auto errmsg = "DirectionSensor requires a DirectionSensorDummy as its parent.";
        std::cerr << errmsg << std::endl;
        throw std::invalid_argument(errmsg);
    }
    this->sensor_->SetActive(true);

	this->output_ = 0.0;
	// Create transport node
	node_.reset(new gz::transport::Node());
	node_->Init();
	
	// subscribe to sound plugin messages
    soundPluginSub_ = node_->Subscribe("~/revolve/drive_direction_update", &DirectionSensor::OnDirUpdate, this);
	
	// connect to the update signal
	this->updateConnection_ = this->sensor_->ConnectUpdated(
        boost::bind(&DirectionSensor::OnUpdate, this, this->sensor_));

    // this is the vector that represents the drive direction
    this->driveDirection_ = ::gz::math::Vector3(0, 0, 0);

    // this is the relative pose of this sensor in the coordinate system of the parent link (never changes)
    this->sensorPose_ = this->sensor_->GetPose();

    // this is the sensor axis in the link coordinate system (never changes)
    this->sensorAxis_ = this->sensorPose_.rot.RotateVector(::gz::math::Vector3(0, 0, 1));

    // name of the parent link
    std::string parentLinkName = this->sensor_->GetParentName();

    // ptr to the parent link
    this->linkPtr_ = this->model_->GetLink( parentLinkName );
    if (!(this->linkPtr_)) {
        std::string errMes("Sound sensor: could not find the link: ");
        errMes.append(parentLinkName);
        throw std::runtime_error(errMes);
    }
}

DirectionSensor::~DirectionSensor() {}


void DirectionSensor::OnDirUpdate(const boost::shared_ptr<::gazebo::msgs::Vector3d const> &_msg)
{
    // std::cout << "DRIVE DIR UPDATED: " << _msg->x() << ", " << _msg->y() << ", " << _msg->z() << std::endl;
    this->driveDirection_.Set(_msg->x(), _msg->y(), _msg->z());
}


void DirectionSensor::OnUpdate(::gazebo::sensors::SensorPtr /*_parentSensor*/)
{
	this->calculateOutput();
}


void DirectionSensor::calculateOutput()
{
    // this is the absolute pose of the parent link in the world coordinate system:
    ::gz::math::Pose linkPose = this->linkPtr_->GetWorldCoGPose();

    // this is the sensor axis in the world coordinate system:
    ::gz::math::Vector3 sensorAxis = linkPose.rot.RotateVector(this->sensorAxis_);

    /// FOR DEBUG: //// ////
    // std::cout << "sensorAxis: " << sensorAxis.x << "," << sensorAxis.y << "," << sensorAxis.z << std::endl;
    //// //// //// //// ////

    double dot = sensorAxis.Dot(this->driveDirection_);
    if (dot < 0) { dot = 0; }

    /// FOR DEBUG: //// ////
    // std::cout << "output: " << dot << std::endl;
    //// //// //// //// ////

    this->output_ = dot;
}


void DirectionSensor::read(double * input) {
	input[0] = this->output_;
}

	
} // namespace gazebo
} // namespace revolve
