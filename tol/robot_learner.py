from operator import itemgetter

# ToL
from .convert import NeuralNetworkParser
from .logging import logger

# NEAT
from neat import NEAT, validate_genotype


class RobotLearner(object):

    def __init__(self, world, robot, brain_spec, mutator, conf):
        self.world = world
        self.robot = robot
        self.nn_parser = NeuralNetworkParser(brain_spec)
        self.mutator = mutator

        self.evaluation_queue = []
        self.brain_velocity = []
        self.generation_number = 0
        self.total_brains_evaluated = 0

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
        future = await self.world.run_brain(self.robot.name, msg)
        return (await future).fitness


    async def run(self, world, logging_callback=None):
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

            self.evaluation_queue = self.evolution.produce_new_generation(self.brain_velocity)

            _, best_fitness_in_gen = max(self.brain_velocity, key = itemgetter(1))
            logger.info("best in gen: {}".format(best_fitness_in_gen))

            # do logging stuff
            if logging_callback:
                self.exec_logging_callback(logging_callback, self.brain_velocity)

            self.brain_velocity = []
            self.generation_number += 1
            logger.info("GENERATION #{}".format(self.generation_number))





    # def set_parameters(self, conf):
    #     """
    #     convenience function to set learning parameters from the config object
    #     :param conf:
    #     :return:
    #     """
    #     self.evaluation_time = conf.evaluation_time
    #     self.warmup_time = conf.warmup_time

    #     self.evaluation_time_sigma = conf.evaluation_time_sigma
    #     self.weight_mutation_sigma = conf.weight_mutation_sigma
    #     self.param_mutation_sigma = conf.param_mutation_sigma

    #     self.max_generations = conf.max_generations
    #     self.repeat_evaluations = conf.repeat_evaluations

    #     self.asexual = conf.asexual



    def robot_to_genotype(self, robot):
        pb_robot = robot.tree.to_robot()
        return self.nn_parser.brain_to_genotype(pb_robot.brain, self.mutator, protect=True)



    def get_init_brains(self):

        '''
        generate an initial population by mutating the default brain
        :return:
        '''

        # get default brain from robot morphology:
        init_genotype = self.robot_to_genotype(self.robot)

        # FOR DEBUG
        ##########################################
        print("initial genotype:")
        print(init_genotype)
        ##########################################
        init_pop = self.evolution.produce_init_generation(init_genotype)
        return init_pop



    # @trollius.coroutine
    # def activate_brain(self, world, brain):

    #     # pause world:
    #     yield From(wait_for(world.pause(True)))
    #     yield From(self.insert_brain(world, brain))
    #     # unpause world:
    #     yield From(wait_for(world.pause(False)))



    # @trollius.coroutine
    # def insert_brain(self, world, brain_genotype):
    #     pb_robot = self.robot.tree.to_robot()
    #     pb_body = pb_robot.body
    #     pb_brain = self.nn_parser.genotype_to_brain(brain_genotype)

    #     # delete robot with old brain:
    #     yield From(world.delete_robot(self.robot))
    #     try:
    #         # create and insert robot with new brain:
    #         tree = Tree.from_body_brain(pb_body, pb_brain, self.body_spec)
    #     except Exception as ex:
    #         print(brain_genotype)
    #         raise ex

    #     pose = Pose(position=self.insert_pos,
    #                 rotation=rotate_vertical(random.random()*3.1415*2.0))
    #     self.robot = yield From(wait_for(world.insert_robot(tree, pose)))


    # def reset_fitness(self):
    #     self.fitness = 0
    #     if self.robot is None:
    #         self.initial_position = self.insert_pos
    #     else:
    #         self.initial_position = self.robot.last_position
    #     self.last_position = self.initial_position
    #     self.traveled_distance = 0


    # def update_fitness(self):
    #     current_position = self.robot.last_position

    #     # displacement from the last update (this is useful if we want to calculate path length):
    #     diff = math.sqrt(pow(current_position[0] - self.last_position[0], 2) + \
    #                      pow(current_position[1] - self.last_position[1], 2))

    #     self.traveled_distance += diff
    #     self.last_position = current_position

    #     # displacement from the starting position:
    #     displacement = math.sqrt(pow(current_position[0] - self.initial_position[0], 2) + \
    #                              pow(current_position[1] - self.initial_position[1], 2))

    #     self.fitness = displacement




    # @trollius.coroutine
    # def update(self, world, logging_callback=None):
    #     old_state = self.state_switch.get_current_state()
    #     state = self.state_switch.update(world.get_world_time())

    #     # if old_state != state:
    #     #     print('state: {0}, time = {1}, fitness = {2}'.format(state, world.get_world_time(), self.get_fitness()))

    #     if state == 'warmup':
    #         self.reset_fitness()

    #     elif state == 'evaluate':
    #         self.update_fitness()

    #     elif state == 'next_brain':

    #         print("Evaluation over")
    #         print("%%%%%%%%%%%%%%%%%%\n\nEvaluated {0} brains".format(str(self.total_brains_evaluated+1)))
    #         print("queue length = {0}".format(len(self.evaluation_queue)))
    #         print("distance covered: {0}".format(self.fitness ))
    #         print("evaluation time was {0}s\n\n%%%%%%%%%%%%%%%%%%".format(self.evaluation_time_actual))

    #         self.fitness_buffer.append(self.fitness / self.evaluation_time_actual)


    #         # # set another drive direction
    #         # yield From(world.set_drive_direction(0.5, 0.75, 0.))

    #         # if repeated brain evaluation is over
    #         if len(self.fitness_buffer) >= self.repeat_evaluations:
    #             yield From(wait_for(world.pause(True)))

    #             aver_fitness = sum(self.fitness_buffer) / float(len(self.fitness_buffer))
    #             self.brain_velocity.append((self.evaluation_queue[self.active_brain], aver_fitness))
    #             print("Brain evaluations are over, average result = {0} ".format(aver_fitness))

    #             self.active_brain += 1

    #             # if all brains are evaluated, produce new generation:
    #             if self.active_brain >= len(self.evaluation_queue):
    #                 self.active_brain = 0
    #                 self.evaluation_queue = self.evolution.produce_new_generation(self.brain_velocity)

    #                 # do logging stuff
    #                 if logging_callback:
    #                     self.exec_logging_callback(logging_callback, self.brain_velocity)

    #                 self.brain_velocity = []
    #                 self.generation_number += 1
    #                 print("GENERATION #{}".format(self.generation_number))


    #         # make snapshot (disable when learning is online, crashes only happen when offline):
    #         yield From(world.create_snapshot())

    #         # insert the next brain:
    #         yield From(self.activate_brain(world, self.evaluation_queue[self.active_brain]))

    #         # -----------------------------------------------------------------------------------
    #         # if we are past this line, the simulator did not crash while inserting a new brain
    #         # -----------------------------------------------------------------------------------

    #         if len(self.fitness_buffer) >= self.repeat_evaluations:
    #             del self.fitness_buffer[:]
    #             self.total_brains_evaluated += 1

    #         self.reset_fitness()
    #         # randomize evaluation time:
    #         self.evaluation_time_actual = self.evaluation_time + \
    #                     random.gauss(0, self.evaluation_time_sigma)

    #         if self.evaluation_time_actual < 0:
    #             self.evaluation_time_actual = 0.5

    #         # set new evaluation time
    #         self.state_switch.set_duration('evaluate', self.evaluation_time_actual)

    #         # switch state to 'warmup'
    #         self.state_switch.switch_to_state('warmup', world.get_world_time())


    #     # if termination criteria are met, return True:
    #     if self.generation_number >= self.max_generations:
    #         raise Return(True)

    #     else:
    #         raise Return(False)



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
        out += "warmup  time         set to {0}\n".format(self.warmup_time)
        out += "evaluation repeats   set to {0}\n".format(self.repeat_evaluations)
        out += "max number of generations set to {0}\n".format(self.max_generations)
        out += "asexual reproduction: {0}\n".format(self.asexual)
        return out
