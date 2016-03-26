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
from ..util import Timers, StateSwitch
from .encoding import Crossover, GeneticEncoding, validate_genotype
from .convert import NeuralNetworkParser


class RobotLearner:

    def __init__(self, world, robot, body_spec, brain_spec, mutator,
                 population_size, tournament_size, num_children,
                 evaluation_time, warmup_time,
                 evaluation_time_sigma,
                 weight_mutation_probability, weight_mutation_sigma,
                 param_mutation_probability, param_mutation_sigma,
                 structural_mutation_probability, max_num_generations,
                 speciation_threshold,
                 repeat_evaluations=1):
        self.robot = robot
        self.active_brain = None

        self.fitness = 0
        self.traveled_distance = 0

        self.initial_position = None
        self.last_position = None

        self.reset_fitness()

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

        # experiment parameters:
        self.pop_size = population_size
        if self.pop_size < 2:
            self.pop_size = 2

        self.tournament_size = tournament_size
        if self.tournament_size > self.pop_size:
            self.tournament_size = self.pop_size
        if self.tournament_size < 2:
            self.tournament_size = 2

        self.num_children = num_children

        self.evaluation_time = evaluation_time
        self.warmup_time = warmup_time
        self.evaluation_time_sigma = evaluation_time_sigma
        self.evaluation_time_actual = evaluation_time

        self.weight_mutation_probability = weight_mutation_probability
        self.weight_mutation_sigma = weight_mutation_sigma
        self.param_mutation_probability = param_mutation_probability
        self.param_mutation_sigma = param_mutation_sigma
        self.structural_mutation_probability = structural_mutation_probability
        self.max_generations = max_num_generations

        self.speciation_threshold = speciation_threshold

        self.repeat_evaluations = repeat_evaluations


        self.state_switch = StateSwitch(['warmup', 'evaluate', 'next_brain'], world.get_world_time())

        self.state_switch.set_duration('warmup', self.warmup_time)
        self.state_switch.set_duration('evaluate', self.evaluation_time_actual)


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

        # create and insert robot with new brain:
        tree = Tree.from_body_brain(pb_body, pb_brain, self.body_spec)
        pose = Pose(position=Vector3(0, 0, 0))
        self.robot = yield From(wait_for(world.insert_robot(tree, pose)))


    def reset_fitness(self):
        self.fitness = 0
        if self.robot is None:
            self.initial_position = Vector3(0,0,0)
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

        # # fitness is a combination of displacement and traveled distance:
        # self.fitness = 5*displacement + self.traveled_distance

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
            print "evaluation time was {0}s".format(self.evaluation_time_actual)
            print "simulation time: {0}\n\n%%%%%%%%%%%%%%%%%%".format(world.get_world_time())

            self.brain_fitness[self.active_brain] = self.get_fitness() / self.evaluation_time_actual
            self.brain_velocity[self.active_brain] =  self.get_fitness() / self.evaluation_time_actual

            # make snapshot:
            yield From(world.create_snapshot())


            # if all brains are evaluated, produce new generation:
            if len(self.evaluation_queue) == 0:

                # distribute fitness based on similarity:
                self.share_fitness()

                # this method fills the evaluation queue with new brains:
                self.produce_new_generation(logging_callback)
                self.generation_number += 1

            # continue evaluating brains from the queue:
            next_brain = self.evaluation_queue[0]
            yield From(self.activate_brain(world, next_brain))

            # -----------------------------------------------------------------------------------
            # if we are past this line, the simulator did not crash while deleting a robot
            # -----------------------------------------------------------------------------------

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
            self.state_switch.switch_to_state('warmup')


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
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.items()]
        brain_velocity_list = [(br, velo) for br, velo in self.brain_velocity.items()]

        # do not store information about old generations:
        self.brain_fitness.clear()
        self.brain_velocity.clear()

        # sort parents from best to worst:
        brain_fitness_list = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse=True)
        brain_velocity_list = sorted(brain_velocity_list, key = lambda elem: elem[1], reverse=True)

        parent_pairs = []

        # create children:
        for _ in range(self.num_children):

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
            log_data = {}
            best_genotypes_string = ""
            all_genotypes_string = ""

            # Log best 3 genotypes in this generation:
            best_genotypes_string += "generation #{0}\n".format(self.generation_number)
            for i in range(3):
                best_genotypes_string += "velocity : {0}\n".format(brain_velocity_list[i][1])
                best_genotypes_string += brain_velocity_list[i][0].to_yaml()
                best_genotypes_string += "\n"

            # Log velocity values of all genotypes in this generation:
            # Log all genotypes in the curent generation to a separate file:
            velocities_string = "- generation: {0}\n  velocities:\n".format(self.generation_number)
            for i in range(len(brain_velocity_list)):
                velocities_string += "  - {0}\n".format(brain_velocity_list[i][1])
                all_genotypes_string += "velocity : {0}\n".format(brain_velocity_list[i][1])
                all_genotypes_string += brain_velocity_list[i][0].to_yaml()
                all_genotypes_string += "\n"

            log_data["velocities.log"] = velocities_string
            log_data["genotypes.log"] = best_genotypes_string
            log_data["gen_{0}_genotypes.log".format(self.generation_number)] = all_genotypes_string
            logging_callback(log_data)


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
        if random.random() < self.structural_mutation_probability:
#            print "applying structural mutation..."

            # if no connections, add connection
            if len(child_genotype.connection_genes) == 0:
#                print "inserting new CONNECTION..."
                self.mutator.add_connection_mutation(child_genotype, self.mutator.new_connection_sigma)
                validate_genotype(child_genotype, "inserting new CONNECTION created invalid genotype")
#                print "inserting new CONNECTION successful"

            # otherwise add connection or neuron with equal probability
            else:
                if random.random() < 0.5:
#                    print "inserting new CONNECTION..."
                    self.mutator.add_connection_mutation(child_genotype, self.mutator.new_connection_sigma)
                    validate_genotype(child_genotype, "inserting new CONNECTION created invalid genotype")
#                    print "inserting new CONNECTION successful"

                else:
 #                   print "inserting new NEURON..."
                    self.mutator.add_neuron_mutation(child_genotype)
                    validate_genotype(child_genotype, "inserting new NEURON created invalid genotype")
 #                   print "inserting new NEURON successful"
        return child_genotype


    def select_for_tournament(self, candidates):

        selected = sorted(random.sample(candidates, self.tournament_size), key = lambda elem: elem[1], reverse=True)
        return selected


    # this method should be called when the learning is over to get a robot with the best brain
    def get_final_robot(self, world):
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.iteritems()]
        best_brain = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse = True)[0]

        self.activate_brain(world, best_brain)
        return self.robot


    def robot_to_genotype(self, robot):
        pb_robot = robot.tree.to_robot()
        return self.nn_parser.brain_to_genotype(pb_robot.brain, self.mutator)


    def print_parameters(self):
        print "population size      set to {0}".format(self.pop_size)
        print "tournament size      set to {0}".format(self.tournament_size)
        print "number of children   set to {0}".format(self.num_children)
        print "evaluation time      set to {0}".format(self.evaluation_time)
        print "warmup  time         set to {0}".format(self.warmup_time)
        print "speciation threshold set to {0}".format(self.speciation_threshold)
        print "max number of generations set to {0}".format(self.max_generations)