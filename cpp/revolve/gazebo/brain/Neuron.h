#ifndef REVOLVE_GAZEBO_BRAIN_NEURON_H_
#define REVOLVE_GAZEBO_BRAIN_NEURON_H_

#include "Brain.h"
#include <cstdlib>
#include <utility>
#include <map>
#include <string>

namespace revolve {
namespace gazebo {


class Neuron
{
public:
	Neuron(const std::string &id);
	virtual ~Neuron() {};
	virtual double CalculateOutput(double t) = 0;

	void AddIncomingConnection(const std::string &socketName, NeuralConnectionPtr connection);
	void DeleteIncomingConections();
	
	double GetOutput() const;

	virtual void SetInput(double value) {};

	void Update(double t);

	void FlipState();

	std::string GetSocketId() const;

	const std::string &Id() const;

protected:

	std::vector<std::pair<std::string, NeuralConnectionPtr> > incomingConnections_;
	double output_;
	double newOutput_;

	std::string id_;

};

}
}
#endif // REVOLVE_GAZEBO_BRAIN_NEURON_H_