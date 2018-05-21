#include "ExtendedNeuralNetwork.h"

#include "../motors/Motor.h"
#include "../sensors/Sensor.h"
#include <fstream>
#include <iostream>

namespace gz = gazebo;

namespace revolve {
namespace gazebo {

ExtendedNeuralNetwork::ExtendedNeuralNetwork(std::string modelName, sdf::ElementPtr node,
				  std::vector< MotorPtr > & motors, std::vector< SensorPtr > & sensors)
{
	
	// Create transport node
	node_.reset(new gz::transport::Node());
	node_->Init();

    // remember the name of the robot
    modelName_ = modelName;

  	// Listen to network modification requests
	alterSub_ = node_->Subscribe("~/"+modelName+"/modify_neural_network",
								 &ExtendedNeuralNetwork::modify, this);

    responsePub_ = node_->Advertise<gz::msgs::Response>("~/"+modelName+"/modify_neural_network_response");



	// Map neuron sdf elements to their id's
    std::map<std::string, sdf::ElementPtr> neuronDescriptions;

    // // Map neuron id strings to Neuron objects
    // std::map<std::string, NeuronPtr> idToNeuron;


	// List of all hidden neuron id's
	std::vector<std::string> hiddenIds;

	// Number of input neurons for mapping them to the input buffer
	numInputNeurons_ = 0;

	// Number of output neurons for mapping them to the output buffer
	numOutputNeurons_ = 0;

	// Number of hidden neurons
	numHiddenNeurons_ = 0;

	// Get the first sdf neuron element
    auto neuron = node->HasElement("rv:neuron") ? node->GetElement("rv:neuron") : sdf::ElementPtr();


    while (neuron) {
		if (!neuron->HasAttribute("layer") || !neuron->HasAttribute("id")) {
			std::cerr << "Missing required neuron attributes (id or layer). '" << std::endl;
			throw std::runtime_error("Robot brain error");
		}
		auto layer = neuron->GetAttribute("layer")->GetAsString();
		auto neuronId = neuron->GetAttribute("id")->GetAsString();


		// check if a neuron with this id has been already added
		if (neuronDescriptions.count(neuronId)) {
			std::cerr << "Duplicate neuron ID '"
					<< neuronId << "'" << std::endl;
			throw std::runtime_error("Robot brain error");
		}

		// add this neuron to the id->sdf map
		neuronDescriptions[neuronId] = neuron;

		// add the neuron id to the appropriate list of id's
		if ("input" == layer) {
//			inputIds.push_back(neuronId);
		}

		else if ("output" == layer) {
//			outputIds.push_back(neuronId);
		}

		else if ("hidden" == layer) {
			hiddenIds.push_back(neuronId);
		}

		else {
			std::cerr << "Unknown neuron layer '" << layer << "'." << std::endl;
			throw std::runtime_error("Robot brain error");
		}

		neuron = neuron->GetNextElement("rv:neuron");
	}



	// Add output neurons for motors:

	// map of numbers of output neurons for each body part
	std::map<std::string, unsigned int> outputCountMap;

	for (auto it = motors.begin(); it != motors.end(); ++it) {
		auto motor = *it;
		auto partId = motor->partId();

		if (!outputCountMap.count(partId)) {
			outputCountMap[partId] = 0;
		}

		for (unsigned int i = 0, l = motor->outputs(); i < l; ++i) {
			std::stringstream neuronId;
			neuronId << partId << "-out-" << outputCountMap[partId];
			outputCountMap[partId]++;

			auto neuronDescription = neuronDescriptions.find(neuronId.str());
			if (neuronDescription == neuronDescriptions.end()) {
				std::cerr << "Required output neuron " << neuronId.str() <<
						" for motor could not be located"
						<< std::endl;
				throw std::runtime_error("Robot brain error");
			}
			
			auto newNeuron = this->neuronHelper(neuronDescription->second);
			idToNeuron_[neuronId.str()] = newNeuron;
			
		}
	}


	// Add input neurons for sensors:

	// map of number of input neurons for each part:

	std::map<std::string, unsigned int> inputCountMap;

	for (auto it = sensors.begin(); it != sensors.end(); ++it) {
		auto sensor = *it;
		auto partId = sensor->partId();

		if (!inputCountMap.count(partId)) {
			inputCountMap[partId] = 0;
		}

		for (unsigned int i = 0, l = sensor->inputs(); i < l; ++i) {
			std::stringstream neuronId;
			neuronId << partId << "-in-" << inputCountMap[partId];
			inputCountMap[partId]++;

			auto neuronDescription = neuronDescriptions.find(neuronId.str());
			if (neuronDescription == neuronDescriptions.end()) {
				std::cerr << "Required input neuron " << neuronId.str() <<
						" for sensor could not be located"
						<< std::endl;
				throw std::runtime_error("Robot brain error");
			}

			auto newNeuron = this->neuronHelper(neuronDescription->second);
			idToNeuron_[neuronId.str()] = newNeuron;
		}
	}

	// initialize the array for sensor inputs:
	inputs_ = new double[numInputNeurons_];
	outputs_ = new double[numOutputNeurons_];


	// Add hidden neurons:
	for (auto it = hiddenIds.begin(); it != hiddenIds.end(); ++it) {
		auto neuronDescription = neuronDescriptions.find(*it);
		auto newNeuron = this->neuronHelper(neuronDescription->second);
		idToNeuron_[*it] = newNeuron;
	}


	// Add connections:
	auto connection = node->HasElement("rv:neural_connection") ? node->GetElement("rv:neural_connection") : sdf::ElementPtr();
	while (connection) {
		if (!connection->HasAttribute("src") || !connection->HasAttribute("dst")
				|| !connection->HasAttribute("weight")) {
			std::cerr << "Missing required connection attributes (`src`, `dst` or `weight`)." << std::endl;
			throw std::runtime_error("Robot brain error");
		}

		auto src = connection->GetAttribute("src")->GetAsString();
		auto dst = connection->GetAttribute("dst")->GetAsString();


		std::string dstSocketName;
		if (connection->HasAttribute("socket")) {
			dstSocketName = connection->GetAttribute("socket")->GetAsString();
		}
		else {
			dstSocketName = "None"; // this is the default socket name
		}

		double weight;
		connection->GetAttribute("weight")->Get(weight);

		// Use connection helper to set the weight
		connectionHelper(src, dst, dstSocketName, weight, idToNeuron_);

		// Load the next connection
		connection = connection->GetNextElement("rv:neural_connection");
	}

}


ExtendedNeuralNetwork::~ExtendedNeuralNetwork()
{
	delete [] inputs_;
	delete [] outputs_;
}


void ExtendedNeuralNetwork::connectionHelper(const std::string &src, const std::string &dst,
	const std::string &socket, double weight, const std::map<std::string, NeuronPtr> &idToNeuron)
{
	auto srcNeuron = idToNeuron.find(src);
	if (srcNeuron == idToNeuron.end()) {
		std::cerr << "Could not find source neuron '" << src << "'" << std::endl;
		throw std::runtime_error("Robot brain error");
	}
	auto dstNeuron = idToNeuron.find(dst);
	if (dstNeuron == idToNeuron.end()) {
		std::cerr << "Could not find destination neuron '" << dst << "'" << std::endl;
		throw std::runtime_error("Robot brain error");
	}

	NeuralConnectionPtr newConnection(new NeuralConnection(
		srcNeuron->second,
		dstNeuron->second,
		weight
	));

	// Add reference to this connection to the destination neuron
	(dstNeuron->second)->AddIncomingConnection(socket, newConnection);
	connections_.push_back(newConnection);
}


NeuronPtr ExtendedNeuralNetwork::neuronHelper(sdf::ElementPtr neuron)
{
	if (!neuron->HasAttribute("type")) {
		std::cerr << "Missing required `type` attribute for neuron." << std::endl;
		throw std::runtime_error("Robot brain error");
	}

	if (!neuron->HasAttribute("layer")) {
		std::cerr << "Missing required `layer` attribute for neuron." << std::endl;
		throw std::runtime_error("Robot brain error");
	}

	auto type = neuron->GetAttribute("type")->GetAsString();
	auto layer = neuron->GetAttribute("layer")->GetAsString();
	auto id = neuron->GetAttribute("id")->GetAsString();

	// map <std::string, double> of parameter names and values
	auto params = parseSDFElement(neuron);

	return this->addNeuron(id, type, layer, params);
}


NeuronPtr ExtendedNeuralNetwork::neuronHelper(const revolve::msgs::Neuron & neuron)
{
	auto type = neuron.type();
	auto layer = neuron.layer();
	auto id = neuron.id();
	std::map<std::string, double> params;
	for (int i = 0; i < neuron.param_size(); ++i) {
		auto param = neuron.param(i);

		// ignore params without names
		if (param.has_name()) {
			auto paramVal = param.value();
			auto paramName = param.name();
			std::stringstream paramNameRevolve;
			paramNameRevolve << "rv:" << paramName;
			params[paramNameRevolve.str()] = paramVal;
		}
	}

	return this->addNeuron(id, type, layer, params);
}



NeuronPtr ExtendedNeuralNetwork::addNeuron(
	const std::string &neuronId,
	const std::string &neuronType,
	const std::string &neuronLayer, // can be 'hidden', 'input' or 'output'
	const std::map<std::string, double> &params)
{
	NeuronPtr newNeuron;

	if ("input" == neuronLayer) {
		newNeuron.reset(new InputNeuron(neuronId, params));

		this->inputNeurons_.push_back(newNeuron);
		inputPositionMap_[newNeuron] = numInputNeurons_;
		numInputNeurons_++;
	}

	else {

		if ("Sigmoid" == neuronType) {
			newNeuron.reset(new SigmoidNeuron(neuronId, params));
		}
		else if ("Simple" == neuronType) {
			newNeuron.reset(new LinearNeuron(neuronId, params));
		}
		else if ("Oscillator" == neuronType) {
			newNeuron.reset(new OscillatorNeuron(neuronId, params));
		}
		else if ("V-Neuron" == neuronType) {
			newNeuron.reset(new VOscillator(neuronId, params));
		}
		else if ("X-Neuron" == neuronType) {
			newNeuron.reset(new XOscillator(neuronId, params));
		}
		else if ("Bias" == neuronType) {
			newNeuron.reset(new BiasNeuron(neuronId, params));
		}
		else if ("Leaky" == neuronType) {
			newNeuron.reset(new LeakyIntegrator(neuronId, params));
		}
		else if ("DifferentialCPG" == neuronType) {
			newNeuron.reset(new DifferentialCPG(neuronId, params));
		}
		else {
			std::cerr << "Unsupported neuron type `" << neuronType << '`' << std::endl;
			throw std::runtime_error("Robot brain error");
		}

		if ("output" == neuronLayer) {
			this->outputNeurons_.push_back(newNeuron);
			outputPositionMap_[newNeuron] = numOutputNeurons_;
			numOutputNeurons_++;
		}
		else { // if neuronLayer is 'hidden'
			this->hiddenNeurons_.push_back(newNeuron);
			numHiddenNeurons_++;
		}
	}

	this->allNeurons_.push_back(newNeuron);
	return newNeuron;
}


void ExtendedNeuralNetwork::update(const std::vector<MotorPtr>& motors,
		const std::vector<SensorPtr>& sensors,
		double t, double step) 
{
	boost::mutex::scoped_lock lock(networkMutex_);

	// Read sensor data into the input buffer
	unsigned int p = 0;
	for (auto sensor : sensors) {
		sensor->read(&inputs_[p]);
		p += sensor->inputs();
	}

	// Feed inputs into the input neurons
	for (auto it = inputNeurons_.begin(); it != inputNeurons_.end(); ++it) {
		auto inNeuron = *it;
		int pos = inputPositionMap_[inNeuron];
		inNeuron->SetInput(inputs_[pos]);
	}

	// Calculate new states of all neurons
	for (auto it = allNeurons_.begin(); it != allNeurons_.end(); ++it) {
		(*it)->Update(t);
	}


	// Flip states of all neurons
	for (auto it = allNeurons_.begin(); it != allNeurons_.end(); ++it) {
		(*it)->FlipState();
	}


	for (auto it = outputNeurons_.begin(); it != outputNeurons_.end(); ++it) {
		auto outNeuron = *it;
		int pos = outputPositionMap_[outNeuron];
		outputs_[pos] = outNeuron->GetOutput();
	}

	
	// Send new signals to the motors
	p = 0;
	for (auto motor: motors) {
		motor->update(&outputs_[p], step);
		p += motor->outputs();
	}
}



void ExtendedNeuralNetwork::flush()
{
	// Delete all references to incoming connections from neurons
	for (auto it = allNeurons_.begin(); it != allNeurons_.end(); ++it) {
		(*it)->DeleteIncomingConections();
	}

	// Nullify the input and output signal buffers
	for (int i = 0; i < numOutputNeurons_; ++i) {
		outputs_[i] = 0;
	}

	for (int i = 0; i < numInputNeurons_; ++i) {
		inputs_[i] = 0;
	}

	// Delete all references to connections from the list
	connections_.clear();

	// Delete all hidden neurons from the id->neuron map
	for (auto it = hiddenNeurons_.begin(); it != hiddenNeurons_.end(); ++it) {
		auto hiddenId = (*it)->Id();
		idToNeuron_.erase(hiddenId);
	}

	// Delete all hidden neurons
	// First delete all neurons
	// Then re-add input and output neurons

	allNeurons_.clear();
	hiddenNeurons_.clear();

	for (auto it = inputNeurons_.begin(); it != inputNeurons_.end(); ++it) {
		allNeurons_.push_back(*it);
	}
	for (auto it = outputNeurons_.begin(); it != outputNeurons_.end(); ++it) {
		allNeurons_.push_back(*it);
	}

    numHiddenNeurons_ = 0;
}



void ExtendedNeuralNetwork::modify(ConstModifyNeuralNetworkPtr & req)
{
	boost::mutex::scoped_lock lock(networkMutex_);

	// delete all connections and hidden neurons
	this->flush();


	// Add requested hidden neurons
	for (int i = 0; i < req->add_hidden_size(); ++i) {
		auto neuron = req->add_hidden(i);
		auto id = neuron.id();

		NeuronPtr newNeuron = neuronHelper(neuron);
		idToNeuron_[id] = newNeuron;
	}

	// Add connections
	for (int i = 0; i < req->set_weights_size(); ++i) {
		auto conn = req->set_weights(i);
		auto src = conn.src();
		auto dst = conn.dst();
		auto weight = conn.weight();

		// Default socket name
		std::string socket = "None";

		// Set non-default socket name
		if (conn.has_socket()) {
			socket = conn.socket();
		}

		// Use connection helper to add the connection
		connectionHelper(src, dst, socket, weight, idToNeuron_);
	}

	// Publish success response (otherwise the sender will wait forever)
	gz::msgs::Response resp;
	resp.set_id(0);
	resp.set_request("modify_neural_network");
	resp.set_response(this->modelName_);
	responsePub_->Publish(resp);
}


std::map<std::string, double> ExtendedNeuralNetwork::parseSDFElement(sdf::ElementPtr elem)
{
	std::map<std::string, double> params;

	auto subElem = elem->GetFirstElement();
	while (subElem) {
		auto elName = subElem->GetName();
		double elValue = subElem->Get<double>();
		params[elName] = elValue;
		subElem = subElem->GetNextElement();
	}

	return params;
}


}
}