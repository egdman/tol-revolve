#include "NeatLearner.h"

#include "../motors/Motor.h"
#include "../sensors/Sensor.h"
#include <fstream>
#include <iostream>

namespace gz = gazebo;

namespace revolve {
namespace gazebo {


NeatLearner::NeatLearner(
    std::string modelName,
    sdf::ElementPtr node,
    const std::vector<MotorPtr>& motors,
    const std::vector<SensorPtr>& sensors)
    : modelName_(modelName)
    , evaluation_time_(30)
    , warmup_time_(3)
    , currentTime_(0)
    , lastTime_(0)
    , currentState_(State::WARMUP)
{
    // Create transport node for message passing
    node_.reset(new gz::transport::Node());
    node_->Init();

    startPosition_[0] = startPosition_[1] = startPosition_[2] = 0.0;
    position_[0] = position_[1] = position_[2] = 0;

    // initialize the controller:
    controller_.reset(new ExtendedNeuralNetwork(modelName_, node, motors, sensors));

    // subscribe to pose updates:
    poseSub_ = node_->Subscribe("~/revolve/robot_poses", &NeatLearner::updatePose, this);

    // advertise topic for posting fitness evaluation results:
    fitnessPub_ = node_->Advertise<gz::msgs::Request>("~/"+modelName+"/fitness");
}



NeatLearner::~NeatLearner()
{}


void NeatLearner::SetDurations(double eval_duration, double warmup_duration)
{
	this->evaluation_time_ = eval_duration;
	this->warmup_time_ = warmup_duration;
}


void NeatLearner::updatePose(const boost::shared_ptr<::gazebo::msgs::PosesStamped const> &msg)
{
	for (int i = 0; i < msg->pose_size(); ++i) {
		auto poseMsg = msg->pose(i);
		auto name =	poseMsg.name();
		
		if (name == this->modelName_) {
			auto position = poseMsg.position();
			this->position_[0] = position.x();
			this->position_[1] = position.y();
			this->position_[2] = position.z();
		}
	}
	auto timeStamp = msg->time();
	double seconds = (double)timeStamp.sec();
	double nanoseconds = (double)timeStamp.nsec() / 1000000000.0;
	this->currentTime_ = seconds + nanoseconds;

}



void NeatLearner::update(const std::vector<MotorPtr>& motors,
		const std::vector<SensorPtr>& sensors,
		double t, double step) 
{
	// Update the neural network state
	this->controller_->update(motors, sensors, t, step);
	
	std::string stateName;
	if (currentState_ == State::WARMUP) {
		stateName = "WARMUP";

		// Discard displacement during WARMUP
		startPosition_[0] = position_[0];
		startPosition_[1] = position_[1];
		startPosition_[2] = position_[2];


		// If WARMUP is over, switch to EVALUATION
		if (currentTime_ - lastTime_ > this->warmup_time_) {
			lastTime_ = currentTime_;
			currentState_ = State::EVALUATION;
			// std::cout << "Switch to: EVALUATION" << std::endl;
		}
	}

	if (currentState_ == State::EVALUATION) {
		stateName = "EVALUATION";

		//// Do nothing during EVALUATION, wait for the robot to move //////

		// If evaluation is over
		if (currentTime_ - lastTime_ > this->evaluation_time_) {


			//// CALCULATE FITNESS //////

			double dx = position_[0] - startPosition_[0];
			double dy = position_[1] - startPosition_[1];

			double distanceCovered = sqrt(dx*dx + dy*dy);
			double fitness = distanceCovered / (float)(this->evaluation_time_);

			// std::cout << modelName_ << " FITNESS = " << fitness << std::endl;

			// publish fitness value
			gz::msgs::Request fit_msg;
			fit_msg.set_id(0);
			fit_msg.set_request(this->modelName_ + "$fitness");
			fit_msg.set_dbl_data(fitness);
			fitnessPub_->Publish(fit_msg);

			////////// TODO /////////////
			//// REMEMBER FITNESS ///////
			/////// SHARE FITNESS ///////
			//// IF ALL BRAINS EVALUATED, GENERATE NEW BRAINS (ALL THE NEAT THINGS HAPPEN HERE) ////
			//// INSERT NEW BRAIN ///////

			// Switch to WARMUP
			lastTime_ = currentTime_;
			currentState_ = State::WARMUP;
			// std::cout << "Switch to: WARMUP" << std::endl;
		}
	}
	// std::cout << "time = " << currentTime_ << ", x=" << position_[0] << ", y=" << position_[1] << 
	// ", state: " << stateName << std::endl;
}


}
}