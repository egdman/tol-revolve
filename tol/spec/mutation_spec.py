from neat import NetworkSpec, GeneSpec, NumericParamSpec as PS



def get_extended_mutation_spec(neuron_sigma, connection_sigma):
	neuron_specs = [
		GeneSpec("Input"),

		GeneSpec("Sigmoid",
			PS('bias', -1., 1., neuron_sigma),
			PS('gain', 0., 1., neuron_sigma)
		),

		GeneSpec("Simple",
			PS('bias', -1., 1., neuron_sigma),
			PS('gain', 0., 1., neuron_sigma)
		),

		GeneSpec("Oscillator",
			PS("period", 0., 10., neuron_sigma),
            PS("phase_offset", 0., 3.14, neuron_sigma),
            PS("amplitude", 0., 10000., neuron_sigma)
        ),

		GeneSpec("Bias",
			PS('bias', -1., 1., neuron_sigma)
		),


		GeneSpec("DifferentialCPG",
			PS('bias', -1., 1.)
		),


		# these neurons (V-Neuron and X-Neuron) are for the nonlinear oscillator CPG model found in Ijspeert (2005):
		GeneSpec("V-Neuron",
			PS('alpha', 0.05, 10., neuron_sigma),
			PS('tau', 1., 50., neuron_sigma),
			PS('energy', 0., 25., neuron_sigma)
		),
		GeneSpec("X-Neuron",
			PS('tau', 0.01, 5.)
		),
	]

	connection_specs = [
		GeneSpec("default",
			PS('weight', mutation_sigma=connection_sigma, mean_value=0.)
		),
	]

	return NetworkSpec(neuron_specs, connection_specs)





def get_mutation_spec(neuron_sigma, connection_sigma):
	neuron_specs = [
		GeneSpec("Input"),

		GeneSpec("Sigmoid",
			PS('bias', -1., 1., neuron_sigma),
			PS('gain', 0., 1., neuron_sigma)
		),

		GeneSpec("Simple",
			PS('bias', -1., 1., neuron_sigma),
			PS('gain', 0., 1., neuron_sigma)
		),

		GeneSpec("Oscillator",
			PS("period", 0., 10., neuron_sigma),
            PS("phase_offset", 0., 3.14, neuron_sigma),
            PS("amplitude", 0., 10000., neuron_sigma)
        ),
	]

	connection_specs = [
		GeneSpec("default",
			PS('weight', mutation_sigma=connection_sigma, mean_value=0.)
		),
	]

	return NetworkSpec(neuron_specs, connection_specs)