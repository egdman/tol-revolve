#ifndef REVOLVE_SOUND_SENSOR_PLUGIN
#define REVOLVE_SOUND_SENSOR_PLUGIN

#include <revolve/gazebo/Types.h>
#include <revolve/gazebo/sensors/SoundSensor.h>

#include <gazebo/gazebo.hh>
#include <gazebo/common/common.hh>
#include "gazebo/common/Plugin.hh"
#include "gazebo/sensors/sensors.hh"

namespace revolve{
namespace gazebo{

class GAZEBO_VISIBLE SoundSensorPlugin: public ::gazebo::SensorPlugin
{
	public: SoundSensorPlugin();

	public: virtual ~SoundSensorPlugin();

	public: virtual void Load(::gazebo::sensors::SensorPtr _parent, sdf::ElementPtr _sdf);

	protected: virtual void OnUpdate(SoundSensorPtr _sensor);

	protected: SoundSensorPtr parentSensor;
	private: ::gazebo::event::ConnectionPtr connection;
};

} // namespace gazebo
} // namespace revolve

#endif // REVOLVE_SOUND_SENSOR_PLUGIN