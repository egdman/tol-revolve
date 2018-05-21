#ifndef _REVOLVE_DIRECTION_SENSOR_DUMMY_H_
#define _REVOLVE_DIRECTION_SENSOR_DUMMY_H_

#include "gazebo/sensors/Sensor.hh"
#include "gazebo/util/system.hh"

namespace gazebo {
namespace sensors {
	

class GAZEBO_VISIBLE DirectionSensorDummy : public Sensor
{
	public: DirectionSensorDummy();

	public: virtual ~DirectionSensorDummy();

	protected: virtual bool UpdateImpl(bool /*_force*/) {return true;}
};

}
}

#endif // _REVOLVE_DIRECTION_SENSOR_DUMMY_H_