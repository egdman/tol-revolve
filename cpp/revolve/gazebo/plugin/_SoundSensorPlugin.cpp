#include "SoundSensorPlugin.h"


namespace gazebo{
GZ_REGISTER_SENSOR_PLUGIN(revolve::gazebo::SoundSensorPlugin)
}


namespace gz = gazebo; // 'gz' is an alias for the outer 'gazebo' namespace

namespace revolve{
namespace gazebo{

SoundSensorPlugin::SoundSensorPlugin()
{
}

SoundSensorPlugin::~SoundSensorPlugin()
{
	this->parentSensor->DisconnectUpdated(this->connection);
	this->parentSensor.reset();
}


void SoundSensorPlugin::Load(::gz::sensors::SensorPtr _parent, sdf::ElementPtr /*_sdf*/)
{
	this->parentSensor = boost::dynamic_pointer_cast<SoundSensor>(_parent);

	if (!this->parentSensor)
	{
		::gz::gzthrow("SoundSensorPlugin requires a sound sensor as its parent.");
	}

	this->connection = this->parentSensor->ConnectUpdated(
        boost::bind(&SoundSensorPlugin::OnUpdate, this, this->parentSensor));
}


void SoundSensorPlugin::OnUpdate(SoundSensorPtr /*_sensor*/)
{
	// don't know if I need this method or not
}




} // namespace gazebo
} // namespace revolve