#ifndef REVOLVE_GAZEBO_BRAIN_NEATLEARNER_H_
#define REVOLVE_GAZEBO_BRAIN_NEATLEARNER_H_

#include "Brain.h"
#include "ExtendedNeuralNetwork.h"
#include <map>
#include <vector>
#include <string>

#include <gazebo/gazebo.hh>
#include <revolve/msgs/neural_net.pb.h>

namespace revolve {
namespace gazebo {


enum State
{
	WARMUP,
	EVALUATION
};


class NeatLearner : public Brain
{
public:
	NeatLearner(
		std::string modelName,
		sdf::ElementPtr node,
		const std::vector<MotorPtr>& motors,
		const std::vector<SensorPtr>& sensors);

	virtual ~NeatLearner();

	virtual void update(const std::vector< MotorPtr > & motors, const std::vector< SensorPtr > & sensors,
			double t, double step);

	void SetDurations(double eval_duration, double warmup_duration);


protected:

	void updatePose(const boost::shared_ptr<::gazebo::msgs::PosesStamped const> &msg);
	
	// Mutex for updating the network
	boost::mutex networkMutex_;

	// Pointer to the underlying controller
	NeuralNetworkPtr controller_;

	// Transport node
	::gazebo::transport::NodePtr node_;

	// Subscriber to pose updates
	::gazebo::transport::SubscriberPtr poseSub_;

	// Publisher for posting fitness evaluation results
	::gazebo::transport::PublisherPtr fitnessPub_;

	// Name of the robot
    std::string modelName_;

    double startPosition_[3];
    double position_[3];

    // Time stamp
    double currentTime_;
    double lastTime_;

    // Time settings
    double evaluation_time_;
    double warmup_time_;

    State currentState_;

};


}
}

#endif // REVOLVE_GAZEBO_BRAIN_EXTENDEDNEURALNETWORK_H_