from operator import itemgetter

# ToL
from .convert import NeuralNetworkParser
from .logging import logger

# NEAT
from neat import NEAT


class RobotLearner(object):

    def __init__(self, world, robot, brain_spec, mutator, conf):
        self.world = world
        self.robot = robot
        self.mutator = mutator
        self.nn_parser = NeuralNetworkParser(brain_spec)

        self.evaluation_queue = []
        self.brain_velocity = []
        self.generation_number = 0
        self.total_brains_evaluated = 0
        self.max_generations = conf.max_generations

        evo_config = dict(
        pop_size = conf.population_size,
        elite_size = conf.population_size - conf.num_children,
        tournament_size = conf.tournament_size,
        neuron_param_mut_proba = conf.param_mutation_probability,
        connection_param_mut_proba = conf.weight_mutation_probability,
        structural_augmentation_proba = conf.structural_augmentation_probability,
        structural_removal_proba = conf.structural_removal_probability,
        speciation_threshold = conf.speciation_threshold,
        )
        self.evolution = NEAT(mutator=mutator, **evo_config)


    async def evaluate_fitness(self, genome):
        msg = self.nn_parser.genotype_to_modify_msg(genome)
        return (await self.world.run_brain(self.robot.name, msg)).fitness


    async def run(self, world, logging_callback=None):
        self.evaluation_queue = self.create_init_brains()

        while self.generation_number < self.max_generations:
            for genome in self.evaluation_queue:
                fitness = await self.evaluate_fitness(genome)
                self.brain_velocity.append((genome, fitness))

                self.total_brains_evaluated += 1
                left_to_evaluate = len(self.evaluation_queue) - len(self.brain_velocity)

                logger.info("{}/{} : fitness = {:.7f}".format(
                    self.total_brains_evaluated,
                    left_to_evaluate,
                    fitness))

            self.evaluation_queue = list(self.evolution.produce_new_generation(self.brain_velocity))

            _, best_fitness_in_gen = max(self.brain_velocity, key = itemgetter(1))
            logger.info("best in gen: {}".format(best_fitness_in_gen))

            # do logging stuff
            if logging_callback:
                self.exec_logging_callback(logging_callback, self.brain_velocity)

            self.brain_velocity = []
            self.generation_number += 1
            logger.info("GENERATION #{}".format(self.generation_number))


    def create_init_brains(self):

        '''
        generate an initial population by mutating the default brain
        :return:
        '''

        # get default brain from robot morphology:
        brain = self.robot.tree.to_robot().brain
        init_genotype = self.nn_parser.brain_to_genotype(brain, self.mutator, protect=True)

        # FOR DEBUG
        ##########################################
        logger.debug("initial genotype:")
        logger.debug(init_genotype)
        ##########################################
        return self.evolution.produce_init_generation(init_genotype)


    def exec_logging_callback(self, logging_callback, brain_velocity_list, vector_list=None):

        brain_velocity_list = sorted(brain_velocity_list, key=itemgetter(1), reverse=True)

        log_data = {}

        # Log best 3 genotypes in this generation:`
        best_genotypes_string = ""
        best_genotypes_string += "- generation : {0}\n".format(self.generation_number)

        for i in range( min(3, len(brain_velocity_list)) ):
            best_genotypes_string += "  - velocity : {0}\n".format(brain_velocity_list[i][1])
            best_genotypes_string += '    '
            best_genotypes_string += brain_velocity_list[i][0].to_yaml().replace('\n', '\n    ')
            best_genotypes_string += "\n"

        log_data["genotypes.log"] = best_genotypes_string


        # Log velocity values of all genotypes in this generation:
        # Log all genotypes in the curent generation to a separate file:
        velocities_string = "- generation: {0}\n  velocities:\n".format(self.generation_number)
        neuron_sizes_string = "- generation: {0}\n  sizes:\n".format(self.generation_number)
        connection_sizes_string = "- generation: {0}\n  sizes:\n".format(self.generation_number)

        all_genotypes_string = ""
        for i in range(len(brain_velocity_list)):
            velocities_string += "  - {0}\n".format(brain_velocity_list[i][1])
            neuron_sizes_string += "  - {0}\n".format(len(brain_velocity_list[i][0].neuron_genes))
            connection_sizes_string += "  - {0}\n".format(len(brain_velocity_list[i][0].connection_genes))

            all_genotypes_string += "- velocity : {0}\n".format(brain_velocity_list[i][1])
            all_genotypes_string += "  "
            all_genotypes_string += brain_velocity_list[i][0].to_yaml().replace('\n', '\n  ')
            all_genotypes_string += "\n"

    
        log_data["velocities.log"] = velocities_string
        log_data["num_neurons.log"] = neuron_sizes_string
        log_data["num_connections.log"] = connection_sizes_string

        log_data["gen_{0}_genotypes.log".format(self.generation_number)] = all_genotypes_string

        # log additional vectors if present:
        if vector_list is not None:
            vector_string = ""
            for vector in vector_list:
                for val in vector:
                    vector_string += "{0},".format(val)
                vector_string += "\n"
            log_data["gen_{0}_vectors.log".format(self.generation_number)] = vector_string

        # call the logging callback with the data
        logging_callback(log_data)



    def parameter_string(self):
        out = ""
        out += "population size      set to {0}\n".format(self.evolution.pop_size)
        out += "tournament size      set to {0}\n".format(self.evolution.tournament_size)
        out += "elite size           set to {0}\n".format(self.evolution.elite_size)
        out += "speciation threshold set to {0}\n".format(self.evolution.speciation_threshold)
        out += "max number of generations set to {0}\n".format(self.max_generations)
        return out
