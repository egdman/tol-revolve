#include "NeuralConnection.h"

namespace revolve {
namespace gazebo {

NeuralConnection::NeuralConnection(const NeuronPtr &src, const NeuronPtr &dst, double weight):
weight_(weight),
src_(src),
dst_(dst)
{}

double NeuralConnection::GetWeight() const
{
	return weight_;
}

NeuronPtr NeuralConnection::GetInputNeuron() const
{
	return src_;
}

}
}