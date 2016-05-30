from __future__ import absolute_import

from revolve.generate import NeuralNetworkGenerator
from revolve.spec import default_neural_net, NeuralNetImplementation, NeuronSpec, ParamSpec

from ..config import constants


def get_extended_brain_spec(conf):
    """
    Returns the brain specification corresponding to the
    given config.
    :param conf:
    :return:
    """
    epsilon = conf.brain_mutation_epsilon

    return NeuralNetImplementation({
        "Input": NeuronSpec(
            layers=["input"]
        ),

        "Sigmoid": NeuronSpec(
            params=[
                ParamSpec("bias", min_value=-1, max_value=1, default=0, epsilon=epsilon),
                ParamSpec("gain", min_value=0, max_value=1, default=.5, epsilon=epsilon)
            ],
            layers=["output", "hidden"]
        ),

        "Simple": NeuronSpec(
            params=[
                ParamSpec("bias", min_value=-1, max_value=1, epsilon=epsilon),
                ParamSpec("gain", min_value=0, max_value=1, default=.5, epsilon=epsilon)
            ],
            layers=["output", "hidden"]
        ),

        # "Gain": NeuronSpec(
        #     params=[
        #         ParamSpec("gain", min_value=0, max_value=1, default=.5, epsilon=epsilon)
        #     ],
        #     layers=["output", "hidden"]
        # ),

        "Bias": NeuronSpec(
            params=[
                ParamSpec("bias", min_value=-1.0, max_value=1.0, epsilon=epsilon),
            ],
            layers=["output", "hidden"]
        ),

        "Oscillator": NeuronSpec(
            params=[
                ParamSpec("period", min_value=0, max_value=10, epsilon=epsilon),
                ParamSpec("phase_offset", min_value=0, max_value=3.14, epsilon=epsilon),
                ParamSpec("amplitude", min_value=0, default=1, max_value=2, epsilon=epsilon)
            ],
            layers=["output", "hidden"]
        ),


        # these neurons are for the nonlinear oscillator CPG model found in Ijspeert (2005):
        "V-Neuron": NeuronSpec(
            params=[
                ParamSpec("alpha", min_value = 0.05, max_value = 10.0, epsilon = epsilon),
                ParamSpec("tau", min_value = 1.0, max_value = 50.0, epsilon = epsilon),
                ParamSpec("energy", min_value = 0.0, max_value = 25.0, epsilon = epsilon)
            ],
            layers = ["output", "hidden"]
        ),

        "X-Neuron": NeuronSpec(
            params=[
                ParamSpec("tau", min_value = 0.01, max_value = 5.0, epsilon = epsilon),
            ],
            layers = ["output", "hidden"]
        ),

        "DifferentialCPG": NeuronSpec(
            params=[
                ParamSpec("bias", min_value = -1.0, max_value = 1.0, epsilon = epsilon),
            ],
            layers = ["output", "hidden"]
        ),
        
        # # Leaky integrator
        # "Leaky": NeuronSpec(
        #     params=[
        #         ParamSpec("bias", min_value = 0.01, max_value = 10.0, epsilon = epsilon),
        #         ParamSpec("tau", min_value = 0.01, max_value = 10.0, epsilon = epsilon),
        #     ],
        #     layers = ["output", "hidden"]
        # ),

        # "NL-Main": NeuronSpec(
        #     params=[
        #         ParamSpec("a", min_value = 0.01, max_value = 10.0, epsilon = epsilon),
        #         ParamSpec("amplitude", min_value = 0.01, max_value = 10.0, epsilon = epsilon)
        #     ],
        #     layers = ["output", "hidden"]
        # )

        # "NL-Theta": NeuronSpec(
        #     params=[
        #         ParamSpec("freq", min_value = 0.01, max_value = 10.0, epsilon = epsilon)
        #     ],
        #     layers = ["output", "hidden"]
        # )

        # "QuadNeuron": NeuronSpec(
        #     params=[],
        #     layers = ["output", "hidden"]
        # )

    })


