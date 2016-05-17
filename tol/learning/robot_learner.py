import sys
import math
import trollius
from trollius import From, Return, Future
from collections import deque
import random

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# Revolve
from revolve.util import multi_future, wait_for
from revolve.angle import Tree

# ToL
from .encoding import Crossover, GeneticEncoding, validate_genotype
from .convert import NeuralNetworkParser
from ..util import StateSwitch, rotate_vertical

class RobotLearner:

    def __init__(self, world, robot, insert_position, body_spec, brain_spec, mutator, conf):
        self.robot = robot
        self.insert_pos = insert_position
        self.active_brain = None

        self.fitness = 0
        self.traveled_distance = 0

        self.initial_position = None
        self.last_position = None

        self.brain_spec = brain_spec
        self.body_spec = body_spec

        self.nn_parser = NeuralNetworkParser(brain_spec)
        self.mutator = mutator

#        self.timers = Timers(['evaluate', 'warmup'], world.get_world_time())
        self.evaluation_queue = deque()
        self.brain_fitness = {}
        self.brain_velocity = {}
        self.generation_number = 0

        self.total_brains_evaluated = 0

        # set experiment parameters:
        self.set_parameters(conf)

        # list of fitnesses for repeated evaluations:
        self.fitness_buffer = []

        # actual eval. time that is a gaussian random variable centered around the self.evaluation_time:
        self.evaluation_time_actual = self.evaluation_time

        # set durations of warmup and evaluation states:
        self.state_switch = StateSwitch(['warmup', 'evaluate', 'next_brain'], world.get_world_time())
        self.state_switch.set_duration('warmup', self.warmup_time)
        self.state_switch.set_duration('evaluate', self.evaluation_time_actual)

    def set_parameters(self, conf):
        """
        convenience function to set learning parameters from the config object
        :param conf:
        :return:
        """
        self.pop_size = conf.population_size
        if self.pop_size < 2:
            self.pop_size = 2

        self.tournament_size = conf.tournament_size
        if self.tournament_size > self.pop_size:
            self.tournament_size = self.pop_size
        if self.tournament_size < 2:
            self.tournament_size = 2

        self.num_children = conf.num_children

        self.evaluation_time = conf.evaluation_time
        self.warmup_time = conf.warmup_time
        self.evaluation_time_sigma = conf.evaluation_time_sigma

        self.weight_mutation_probability = conf.weight_mutation_probability
        self.weight_mutation_sigma = conf.weight_mutation_sigma
        self.param_mutation_probability = conf.param_mutation_probability
        self.param_mutation_sigma = conf.param_mutation_sigma
        self.structural_mutation_probability = conf.structural_mutation_probability
        self.removal_mutation_probability = conf.removal_mutation_probability
        self.max_generations = conf.max_generations
        self.speciation_threshold = conf.speciation_threshold
        self.repeat_evaluations = conf.repeat_evaluations



    @trollius.coroutine
    def initialize(self, world, init_genotypes=None):
        if init_genotypes is None:
            brain_population = self.get_init_brains()
        else:
            brain_population = init_genotypes

        for br in brain_population:
            validate_genotype(br, "initial generation created invalid genotype")
            self.evaluation_queue.append(br)

        first_brain = self.evaluation_queue.popleft()

        self.reset_fitness()
        yield From(self.activate_brain(world, first_brain))


    def get_init_brains(self):

        '''
        generate an initial population by mutating the default brain
        :return:
        '''

        # get default brain from robot morphology:
        init_genotype = self.robot_to_genotype(self.robot)

        # FOR DEBUG
        ##########################################
        print "initial genotype:"
        print init_genotype.debug_string(True)
        ##########################################
        init_pop = []
        for _ in range(self.pop_size):
            mutated_genotype = init_genotype.copy()

            self.mutator.mutate_weights(
                genotype=mutated_genotype,
                probability=self.weight_mutation_probability,
                sigma=self.weight_mutation_sigma)

            self.mutator.mutate_neuron_params(
                genotype=mutated_genotype,
                probability=self.param_mutation_probability,
                sigma=self.param_mutation_sigma)

            init_pop.append(mutated_genotype)

        return init_pop


    @trollius.coroutine
    def activate_brain(self, world, brain):

        # pause world:
        yield From(wait_for(world.pause(True)))
        yield From(self.insert_brain(world, brain))
        self.active_brain = brain
        # unpause world:
        yield From(wait_for(world.pause(False)))



    @trollius.coroutine
    def insert_brain(self, world, brain_genotype):
        pb_robot = self.robot.tree.to_robot()
        pb_body = pb_robot.body
        pb_brain = self.nn_parser.genotype_to_brain(brain_genotype)

        # delete robot with old brain:
        yield From(world.delete_robot(self.robot))
        try:
            # create and insert robot with new brain:
            tree = Tree.from_body_brain(pb_body, pb_brain, self.body_spec)
        except Exception as ex:
            print brain_genotype.debug_string(True)
            raise ex

        pose = Pose(position=self.insert_pos,
                    rotation=rotate_vertical(random.random()*3.1415*2.0))

        self.robot = yield From(wait_for(world.insert_robot(tree, pose)))


    def reset_fitness(self):
        self.fitness = 0
        if self.robot is None:
            self.initial_position = self.insert_pos
        else:
            self.initial_position = self.robot.last_position
        self.last_position = self.initial_position
        self.traveled_distance = 0


    def update_fitness(self):
        current_position = self.robot.last_position

        # displacement from the last update:
        diff = math.sqrt(pow(current_position[0] - self.last_position[0], 2) + \
                         pow(current_position[1] - self.last_position[1], 2))

        self.traveled_distance += diff
        self.last_position = current_position

        # displacement from the starting position:
        displacement = math.sqrt(pow(current_position[0] - self.initial_position[0], 2) + \
                                 pow(current_position[1] - self.initial_position[1], 2))

        self.fitness = displacement


    def get_fitness(self):
        return self.fitness


    @trollius.coroutine
    def update(self, world, logging_callback=None):
        old_state = self.state_switch.get_current_state()
        state = self.state_switch.update(world.get_world_time())

        # if old_state != state:
        #     print 'state: {0}, time = {1}, fitness = {2}'.format(state, world.get_world_time(), self.get_fitness())

        if state == 'warmup':
            self.reset_fitness()

        elif state == 'evaluate':
            self.update_fitness()

        elif state == 'next_brain':

            print "Evaluation over"

            print "%%%%%%%%%%%%%%%%%%\n\nEvaluated {0} brains".format(str(self.total_brains_evaluated+1))
            print "last evaluated: {0}".format(self.active_brain)
            print "queue length = {0}".format(len(self.evaluation_queue))
            print "fitness (distance covered): {0}".format(self.fitness )
            print "evaluation time was {0}s\n\n%%%%%%%%%%%%%%%%%%".format(self.evaluation_time_actual)
  #          print "simulation time: {0}".format(world.get_world_time())

            self.fitness_buffer.append(self.get_fitness() / self.evaluation_time_actual)

            # if repeated brain evaluation is not over
            if len(self.fitness_buffer) < self.repeat_evaluations:

                # continue evaluating the same brain:
                next_brain = self.active_brain

            # if repeated brain evaluation is over
            else:
                yield From(wait_for(world.pause(True)))
                aver_fitness = sum(self.fitness_buffer) / float(len(self.fitness_buffer))

                self.brain_fitness[self.active_brain] = aver_fitness
                self.brain_velocity[self.active_brain] = aver_fitness
                print "Brain evaluations are over, average result = {0} ".format(aver_fitness)

                # if all brains are evaluated, produce new generation:
                if len(self.evaluation_queue) == 0:

                    # distribute fitness based on similarity:
                    self.share_fitness()

                    # this method fills the evaluation queue with new brains:
                    self.produce_new_generation(logging_callback)
                    self.generation_number += 1

                # continue evaluating brains from the queue:
                next_brain = self.evaluation_queue[0]

            # make snapshot:
            yield From(world.create_snapshot())

            # insert the next brain:
            yield From(self.activate_brain(world, next_brain))

            # -----------------------------------------------------------------------------------
            # if we are past this line, the simulator did not crash while inserting a new brain
            # -----------------------------------------------------------------------------------

            if len(self.fitness_buffer) >= self.repeat_evaluations:
                del self.fitness_buffer[:]
                self.total_brains_evaluated += 1
                self.evaluation_queue.popleft()

            self.reset_fitness()
            # randomize evaluation time:
            self.evaluation_time_actual = self.evaluation_time + \
                        random.gauss(0, self.evaluation_time_sigma)

            if self.evaluation_time_actual < 0:
                self.evaluation_time_actual = 0.5

            # set new evaluation time
            self.state_switch.set_duration('evaluate', self.evaluation_time_actual)

            # switch state to 'warmup'
            self.state_switch.switch_to_state('warmup', world.get_world_time())


        # if termination criteria are met, return True:
        if self.generation_number >= self.max_generations:
            raise Return(True)

        else:
            raise Return(False)


    def share_fitness(self):
        new_fitness = {}

        for cur_brain, cur_fitness in self.brain_fitness.items():
            species_size = 1
            for other_brain, other_fitness in self.brain_fitness.items():
                if not other_brain == cur_brain:
                    distance = GeneticEncoding.get_dissimilarity(other_brain, cur_brain)
                    if distance < self.speciation_threshold:
                        species_size += 1
            new_fitness[cur_brain] = cur_fitness / float(species_size)
            
            # FOR DEBUG
            ################################################
            print 'SHARED FITNESS = {0}, species size = {1}'.format(new_fitness[cur_brain], species_size)
            ################################################

        self.brain_fitness = new_fitness


    def produce_new_generation(self, logging_callback = None):
        # this is list with shared fitnesses:
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.items()]

        # this is list with unshared fitnesses:
        brain_velocity_list = [(br, velo) for br, velo in self.brain_velocity.items()]

        # do not store information about old generations:
        self.brain_fitness.clear()
        self.brain_velocity.clear()

        # sort parents from best to worst:
        brain_fitness_list = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse=True)
        brain_velocity_list = sorted(brain_velocity_list, key = lambda elem: elem[1], reverse=True)


        # brain_list = [br for (br, velo) in brain_velocity_list]
        # hm_params = GeneticEncoding.get_space_map(brain_list, self.brain_spec)
        # vector_list = [br.to_vector(hm_params, self.brain_spec) for br in brain_list]
        #
        # recycled_brains = [br.copy() for br in brain_list]
        # for brain, vector in zip(recycled_brains, vector_list):
        #     brain.from_vector(vector, hm_params, self.brain_spec)


        parent_pairs = []

        # create children:
        for _ in range(self.num_children):

            # we select brains using their shared fitnesses:
            selected = self.select_for_tournament(brain_fitness_list)

            # select 2 best parents from the tournament:
            parent_a = selected[0]
            parent_b = selected[1]

            # first in pair must be the best of two:
            parent_pairs.append((parent_a, parent_b))

        # create children and append them to the queue:
        for i, pair in enumerate(parent_pairs):
            child_genotype = self.produce_child(pair[0][0], pair[1][0])
            self.evaluation_queue.append(child_genotype)

        # bringing the best parents into next generation:
        for i in range(self.pop_size - self.num_children):
            print "saving parent #{0}, velocity = {1}".format(str(i+1), brain_velocity_list[i][1])
            self.evaluation_queue.append(brain_velocity_list[i][0])

        # log important information:
        if logging_callback:
            self.exec_logging_callback(logging_callback, brain_velocity_list)


    def produce_child(self, parent1, parent2):
        # apply crossover:
#        print "applying crossover..."
        child_genotype = Crossover.crossover(parent1, parent2)
        validate_genotype(child_genotype, "crossover created invalid genotype")
#         print "crossover successful"


        # apply mutations:

#         print "applying weight mutations..."
        self.mutator.mutate_weights(
            genotype=child_genotype,
            probability=self.weight_mutation_probability,
            sigma=self.weight_mutation_sigma)
        validate_genotype(child_genotype, "weight mutation created invalid genotype")
#         print "weight mutation successful"


#         print "applying neuron parameters mutations..."
        self.mutator.mutate_neuron_params(
            genotype=child_genotype,
            probability=self.param_mutation_probability,
            sigma=self.param_mutation_sigma)
        validate_genotype(child_genotype, "neuron parameters mutation created invalid genotype")
#        print "neuron parameters mutation successful"


        # apply structural mutations:
        self.apply_structural_mutation(child_genotype)
        return child_genotype


    def apply_structural_mutation(self, genotype):

        # apply augmentation mutation:
        if random.random() < self.structural_mutation_probability:

            # if no connections, add connection
            if len(genotype.connection_genes) == 0:
                self.mutator.add_connection_mutation(genotype, self.mutator.new_connection_sigma)
                validate_genotype(genotype, "inserting new CONNECTION created invalid genotype")

            # otherwise add connection or neuron with equal probability
            else:
                if random.random() < 0.5:
                    self.mutator.add_connection_mutation(genotype, self.mutator.new_connection_sigma)
                    validate_genotype(genotype, "inserting new CONNECTION created invalid genotype")

                else:
                    self.mutator.add_neuron_mutation(genotype)
                    validate_genotype(genotype, "inserting new NEURON created invalid genotype")


        # apply removal mutation:
        if random.random() < self.removal_mutation_probability:
            if random.random() < 0.5:
                self.mutator.remove_connection_mutation(genotype)
                validate_genotype(genotype, "removing a CONNECTION created invalid genotype")
            else:
                self.mutator.remove_neuron_mutation(genotype)
                validate_genotype(genotype, "removing a NEURON created invalid genotype")



    def select_for_tournament(self, candidates):

        selected = sorted(random.sample(candidates, self.tournament_size), key = lambda elem: elem[1], reverse=True)
        return selected


    def exec_logging_callback(self, logging_callback, brain_velocity_list, vector_list=None):

        log_data = {}

        # Log best 3 genotypes in this generation:`
        best_genotypes_string = ""
        best_genotypes_string += "- generation : {0}\n".format(self.generation_number)

        for i in range(3):
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
            neuron_sizes_string += "  - {0}\n".format(brain_velocity_list[i][0].num_neuron_genes())
            connection_sizes_string += "  - {0}\n".format(brain_velocity_list[i][0].num_connection_genes())

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


    def robot_to_genotype(self, robot):
        pb_robot = robot.tree.to_robot()
        return self.nn_parser.brain_to_genotype(pb_robot.brain, self.mutator)


    def parameter_string(self):
        out = ""
        out += "population size      set to {0}\n".format(self.pop_size)
        out += "tournament size      set to {0}\n".format(self.tournament_size)
        out += "number of children   set to {0}\n".format(self.num_children)
        out += "evaluation time      set to {0}\n".format(self.evaluation_time)
        out += "warmup  time         set to {0}\n".format(self.warmup_time)
        out += "speciation threshold set to {0}\n".format(self.speciation_threshold)
        out += "evaluation repeats   set to {0}\n".format(self.repeat_evaluations)
        out += "max number of generations set to {0}\n".format(self.max_generations)
        return out



class RobotLearnerOnline(RobotLearner):

    @trollius.coroutine
    def insert_brain(self, world, brain_genotype):
        '''
        Send a ModifyNeuralNetwork message that contains the new brain
        :param world:
        :param brain_genotype:
        :return:
        '''

        # send a ModifyNeuralNetwork message that contains the new brain:
        msg = self.nn_parser.genotype_to_modify_msg(brain_genotype)
        fut = yield From(world.modify_brain(msg, self.robot.name))
        yield From(fut)



class SoundGaitLearner(RobotLearner):
    def __init__(self, world, robot, body_spec, brain_spec, mutator, conf):
        # coordinates of the sound source:
        self.sound_source_pos = Vector3(0,0,0)

        # initial distance from robot to source:
        self.init_distance = 0

        RobotLearner.__init__(self, world, robot, body_spec, brain_spec, mutator, conf)


    def set_sound_source_pos(self, position):
        self.sound_source_pos = position

    def reset_fitness(self):
        RobotLearner.reset_fitness(self)
        self.init_distance = math.sqrt(pow(self.sound_source_pos[0] - self.initial_position[0], 2) + \
                                 pow(self.sound_source_pos[1] - self.initial_position[1], 2))

    def update_fitness(self):
        current_position = self.robot.last_position
        current_distance = math.sqrt(pow(current_position[0] - self.sound_source_pos[0], 2) + \
                                 pow(current_position[1] - self.sound_source_pos[1], 2))
        self.fitness = self.init_distance - current_distance


class PSOLearner(RobotLearner):

    def __init__(self, world, robot, insert_position, body_spec, brain_spec, mutator, conf):
        RobotLearner.__init__(self, world, robot, insert_position, body_spec, brain_spec, mutator, conf)

        # pairs (brain, velocity):
        self.individual_bests = []

        # list of current brain vectors:
        self.brains = []

        # list of velocities in parameter space:
        self.param_space_velocities = []

        
        loc_coef = conf.pso_local_coef
        glob_coef = conf.pso_global_coef

        # particle swarm optimizer:
        self.pso = PSOptimizer(individual_coef=loc_coef, social_coef=glob_coef)


    @trollius.coroutine
    def initialize(self, world, init_genotypes=None):
        if init_genotypes is None:
            brain_population = self.get_init_brains()
        else:
            brain_population = init_genotypes

        for br in brain_population:
            validate_genotype(br, "initial generation created invalid genotype")
            self.brains.append(br)
            self.individual_bests.append((br.copy(), 0))
            self.evaluation_queue.append(br)

        first_brain = self.evaluation_queue.popleft()

        self.reset_fitness()
        yield From(self.activate_brain(world, first_brain))





    def produce_new_generation(self, logging_callback = None):
        hm_params = GeneticEncoding.get_space_map(self.brains, self.brain_spec)

        # save list of brains sorted by unshared fitness:
        brain_velocity_list = [(br, velo) for br, velo in self.brain_velocity.items()]
        brain_velocity_list = sorted(brain_velocity_list, key=lambda elem: elem[1], reverse=True)

        # save the list of brains sorted by shared fitness:
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.items()]
        brain_fitness_list = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse=True)


        # create a list of elite candidates using unshared fitness:
        num_elite = self.pop_size - self.num_children
        elite_brains = []
        for i in range(num_elite):
            elite_brains.append(brain_velocity_list[i][0])
            print "saving parent #{0}, velocity = {1}".format(str(i+1), brain_velocity_list[i][1])



        
        # PSO PART #########################################################################################
        # update individual bests:
        for i, br in enumerate(self.brains):
            velo = self.brain_velocity[br]

            best_brain = self.individual_bests[i][0]
            best_velo = self.individual_bests[i][1]

            if velo > best_velo:
                self.individual_bests[i] = (br.copy(), velo)

        # find global best:
        global_best_brain = self.individual_bests[0][0]
        global_best_velo = self.individual_bests[0][1]
        for (br, velo) in self.individual_bests:
            if velo > global_best_velo:
                global_best_velo = velo
                global_best_brain = br

        # calculate current positions:
        current_positions = []
        for br in self.brains:
            current_positions.append(br.to_vector(hm_params, self.brain_spec))

        # calculate individual best positions:
        ind_best_positions = []
        for (br, velo) in self.individual_bests:
            ind_best_positions.append(br.to_vector(hm_params, self.brain_spec))

        # calculate global best position:
        global_best_vector = global_best_brain.to_vector(hm_params, self.brain_spec)

        # initialize param space velocities of brains (if not initialized yet)
        if len(self.param_space_velocities) == 0:
            print "initializing parameter space velocities"
            for vec in current_positions:
                param_velo = {}
                for hm, num_params in hm_params:
                    param_velo[hm] = [0 for _ in range(num_params)]
                self.param_space_velocities.append(param_velo)


        # gather parameter space velocity data for debug: #####################
        debug_out = []
        space_map = []
        for hm, num_par in hm_params:
            for i in range(num_par):
                space_map.append(hm)
        debug_out.append(space_map)
        #######################################################################

        # calculate new positions;
        new_positions = []
        for i in range(len(current_positions)):

            # flatten param space velocity dictionary into vector:
            param_velocity_vector = []
            param_velocity_dict = self.param_space_velocities[i]
            for hm, num_params in hm_params:
                subvector = param_velocity_dict.get(hm, None)

                # if velocity data for this hm does not exist (e.g. this hm was added in last generation):
                if subvector is None:
                    for n in range(num_params):
                        param_velocity_vector.append(0)
                else:
                    for val in subvector:
                        param_velocity_vector.append(val)

            # calculate new position for this particle:
            new_pos = self.pso.step(
                ind_best=ind_best_positions[i],
                global_best=global_best_vector,
                current_pos=current_positions[i],
                velocity=param_velocity_vector) # this will change inside the method
            new_positions.append(new_pos)

            # turn velocity vector back into dictionary:
            base_index = 0
            for hm, num_params in hm_params:
                subvector = []
                for j in range(base_index, base_index + num_params):
                    subvector.append(param_velocity_vector[j])
                param_velocity_dict[hm] = subvector
                base_index += num_params
            self.param_space_velocities[i] = param_velocity_dict

            debug_out.append(param_velocity_vector)

        # update brains from new positions:
        num_updated = 0
        for i in range(len(self.brains)):
            if self.brains[i] not in elite_brains:
                self.brains[i].from_vector(new_positions[i], hm_params, self.brain_spec)
                num_updated += 1
        print "{0} brains updated".format(num_updated)
        ####################################################################################################




        # NON-PSO PART #####################################################################################
        # apply non-pso operations (adoption, structural mutation)
        for br in self.brains:
            if br not in elite_brains:
                # adopt other brains' genes:
                tournament = self.select_for_tournament(brain_fitness_list)
                adoptee = tournament[0][0]

                if self.brain_fitness[adoptee] > self.brain_fitness[br]:
                    br.adopt(adoptee)
                    validate_genotype(br, "ADOPTING genes created invalid genotype")

                # apply structural mutation:
                self.apply_structural_mutation(br)
        #####################################################################################################


        # add the brains to the evaluation queue:
        for br in self.brains:
            self.evaluation_queue.append(br)


        # do not store information about old positions:
        self.brain_fitness.clear()
        self.brain_velocity.clear()

        # log important information:
        if logging_callback:
            self.exec_logging_callback(logging_callback, brain_velocity_list, debug_out)



class PSOptimizer:
    def __init__(self, individual_coef, social_coef):
        self.ind_coef = individual_coef
        self.social_coef = social_coef

    def step(self, ind_best, global_best, current_pos, velocity):
        new_pos = [0 for _ in range(len(ind_best))]

        if velocity is None:
            velocity = [0 for _ in range(len(ind_best))]

        for i in range(len(new_pos)):
            accel = self.ind_coef * (ind_best[i] - current_pos[i]) + \
                    self.social_coef * (global_best[i] - current_pos[i])

            velocity[i] += accel

        for i in range(len(new_pos)):
            new_pos[i] = current_pos[i] + velocity[i]

        return new_pos
