from __future__ import absolute_import

from revolve.generate import NeuralNetworkGenerator
from revolve.spec import default_neural_net

from ..config import constants


def get_modified_brain_spec(conf):
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
        "Gain": NeuronSpec(
            params=[
                ParamSpec("gain", min_value=0, max_value=1, default=.5, epsilon=epsilon)
            ],
            layers=["output", "hidden"]
        ),
        "Bias": NeuronSpec(
            params=[
                ParamSpec("bias", min_value=-1, max_value=1, epsilon=epsilon),
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
        )
    })


