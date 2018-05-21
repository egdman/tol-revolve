#include <revolve/gazebo/motors/MotorFactory.h>
#include <revolve/gazebo/sensors/SensorFactory.h>
#include <revolve/gazebo/brain/NeuralNetwork.h>
#include <revolve/gazebo/brain/ExtendedNeuralNetwork.h>

#include <gazebo/sensors/sensors.hh>
#include <gazebo/common/common.hh>
#include <gazebo/physics/physics.hh>

#include <vector>
#include <fstream>
#include <string>

namespace gz = gazebo;
using namespace revolve::gazebo;


int main(int argc, char* argv[])
{
	if (argc < 2) {
		std::cout << "NEED PATH TO SDF FILE" << std::endl;
		return 1;
	}

	char * path = argv[1];
	std::ifstream inFile;
	inFile.open(path, std::ifstream::in);
	std::string sdfString;
	sdfString.assign(std::istreambuf_iterator<char>(inFile), std::istreambuf_iterator<char>() );
	inFile.close();

	std::vector<MotorPtr> motors;
	std::vector<SensorPtr> sensors;


	sdf::SDF sdfRobot;
	sdfRobot.SetFromString(sdfString);

	sdf::ElementPtr rootElem = sdfRobot.Root();

	if (!rootElem) {
		std::cout << "Root element is NULL" << std::endl;
		return 1;
	}

	gz::physics::ModelPtr model(new gz::physics::Model(NULL));

	if (!model) {
		std::cout << "gazebo::physics::Model object is NULL" << std::endl;
		return 1;
	}

	model->Load(rootElem->GetElement("model"));

	auto plugin = rootElem->GetElement("model")->GetElement("plugin");
	auto robotConfig = plugin->GetElement("rv:robot_config");

	if (!robotConfig) {
		std::cout << "rv::robot_config is NULL" << std::endl;
		return 1;
	}

	MotorFactoryPtr motorFactory(new MotorFactory(model));
	SensorFactoryPtr sensorFactory(new SensorFactory(model));



	//// LOAD MOTORS /////////////////////////////////////////
	auto motor = robotConfig->GetElement("rv:motor");
    while (motor) {
    	auto motorObj = motorFactory->create(motor);
    	motors.push_back(motorObj);
    	motor = motor->GetNextElement("rv:motor");
    }
    //////////////////////////////////////////////////////////


    //// LOAD SENSORS ////////////////////////////////////////
    auto sensor = robotConfig->GetElement("rv:sensor");
	while (sensor) {
		auto sensorObj = sensorFactory->create(sensor);
		sensors.push_back(sensorObj);
		sensor = sensor->GetNextElement("rv:sensor");
	}
    //////////////////////////////////////////////////////////




	auto brain = robotConfig->GetElement("rv:brain");

	ExtendedNeuralNetwork *extNN =  new ExtendedNeuralNetwork("robot_name", brain, motors, sensors);
	return 0;
}
