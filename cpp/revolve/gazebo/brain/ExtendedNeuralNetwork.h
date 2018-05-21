#ifndef REVOLVE_GAZEBO_BRAIN_EXTENDEDNEURALNETWORK_H_
#define REVOLVE_GAZEBO_BRAIN_EXTENDEDNEURALNETWORK_H_

#include "Brain.h"
#include "Neuron.h"
#include "NeuralConnection.h"
#include <map>
#include <vector>
#include <string>

#include "LinearNeuron.h"
#include "SigmoidNeuron.h"
#include "OscillatorNeuron.h"
#include "VOscillator.h"
#include "XOscillator.h"
#include "LeakyIntegrator.h"
#include "BiasNeuron.h"
#include "DifferentialCPG.h"

#include "InputNeuron.h"

#include <gazebo/gazebo.hh>
#include <revolve/msgs/neural_net.pb.h>

namespace revolve {
namespace gazebo {

typedef const boost::shared_ptr<revolve::msgs::ModifyNeuralNetwork const> ConstModifyNeuralNetworkPtr;

class ExtendedNeuralNetwork : public Brain
{
public:
	ExtendedNeuralNetwork(std::string modelName, sdf::ElementPtr node,
				  std::vector< MotorPtr > & motors, std::vector< SensorPtr > & sensors);

	virtual ~ExtendedNeuralNetwork();

	virtual void update(const std::vector< MotorPtr > & motors, const std::vector< SensorPtr > & sensors,
			double t, double step);


protected:

		// Mutex for updating the network
	boost::mutex networkMutex_;

	/**
	 * Transport node
	 */
	::gazebo::transport::NodePtr node_;

	/**
	 * Network modification subscriber
	 */
	::gazebo::transport::SubscriberPtr alterSub_;


	/**
	 * Publisher for network modification responses
	 */
	::gazebo::transport::PublisherPtr responsePub_;


	/**
	 * This function creates neurons and adds them to appropriate lists
	 */
	NeuronPtr addNeuron(
		const std::string &neuronId,
		const std::string &neuronType, 
		const std::string &neuronLayer, // can be 'hidden', 'input' or 'output'
		const std::map<std::string, double> &params);


	std::map<std::string, double> parseSDFElement(sdf::ElementPtr elem);

	NeuronPtr neuronHelper(sdf::ElementPtr);
	NeuronPtr neuronHelper(const revolve::msgs::Neuron &);

	void connectionHelper(const std::string &src, const std::string &dst,
	const std::string &socket, double weight, const std::map<std::string, NeuronPtr> &idToNeuron);

	/**
	 * Delete all hidden neurons and all connections
	 */
	void flush();


	/**
	 * Add hidden neurons and connections from a protobuf message
	 */
	void modify(ConstModifyNeuralNetworkPtr &);


    /**
     * Name of the robot
     */
    std::string modelName_;

    // buffer of input values from the sensors
    double * inputs_;

    // buffer of output values for the motors
    double * outputs_;

    std::vector<NeuronPtr> allNeurons_;
	std::vector<NeuronPtr> inputNeurons_;
	std::vector<NeuronPtr> outputNeurons_;
	std::vector<NeuronPtr> hiddenNeurons_;

	// positions for indexing into the outputs_ buffer for each output neuron
	std::map<NeuronPtr, int> outputPositionMap_;

	// positions for indexing into the inputs_ buffer for each input neuron
	std::map<NeuronPtr, int> inputPositionMap_;

	// Map neuron id strings to Neuron objects
	std::map<std::string, NeuronPtr> idToNeuron_;

    std::vector<NeuralConnectionPtr> connections_;

    int numInputNeurons_;
    int numOutputNeurons_;
    int numHiddenNeurons_;

};


}
}

#endif // REVOLVE_GAZEBO_BRAIN_EXTENDEDNEURALNETWORK_H_