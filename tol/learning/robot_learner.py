import math
import trollius
from trollius import From, Return, Future
from collections import deque
import random
from operator import itemgetter

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose

# Revolve
from revolve.util import multi_future, wait_for
from revolve.angle import Tree

# ToL
from .convert import NeuralNetworkParser
from ..util import StateSwitch, rotate_vertical
from ..logging import logger, output_console

# NEAT
from neat import NEAT, validate_genotype



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


        self.evaluation_queue = deque()

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

        evo_conf = dict(
        pop_size = conf.population_size,
        elite_size = conf.population_size - conf.num_children,
        tournament_size = conf.tournament_size,
        neuron_param_mut_proba = conf.param_mutation_probability,
        connection_param_mut_proba = conf.weight_mutation_probability,
        structural_augmentation_proba = conf.structural_augmentation_probability,
        structural_removal_proba = conf.structural_removal_probability,
        speciation_threshold = conf.speciation_threshold,
        )
        self.evolution = NEAT(mutator=mutator, **evo_conf)


    def set_parameters(self, conf):
        """
        convenience function to set learning parameters from the config object
        :param conf:
        :return:
        """
        self.evaluation_time = conf.evaluation_time
        self.warmup_time = conf.warmup_time

        self.evaluation_time_sigma = conf.evaluation_time_sigma
        self.weight_mutation_sigma = conf.weight_mutation_sigma
        self.param_mutation_sigma = conf.param_mutation_sigma

        self.max_generations = conf.max_generations
        self.repeat_evaluations = conf.repeat_evaluations

        self.asexual = conf.asexual




    @trollius.coroutine
    def initialize(self, world, init_genotypes=None):
        # this call establishes minimally viable genome based on robot body morphology
        brain_population = self.get_init_brains()

        if init_genotypes is not None:
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
        print("initial genotype:")
        print(init_genotype)
        ##########################################
        init_pop = self.evolution.produce_init_generation(init_genotype)
        return init_pop




    def robot_to_genotype(self, robot):
        pb_robot = robot.tree.to_robot()
        return self.nn_parser.brain_to_genotype(pb_robot.brain, self.mutator, protect=True)




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
            print(brain_genotype)
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

        # displacement from the last update (this is useful if we want to calculate path length):
        diff = math.sqrt(pow(current_position[0] - self.last_position[0], 2) + \
                         pow(current_position[1] - self.last_position[1], 2))

        self.traveled_distance += diff
        self.last_position = current_position

        # displacement from the starting position:
        displacement = math.sqrt(pow(current_position[0] - self.initial_position[0], 2) + \
                                 pow(current_position[1] - self.initial_position[1], 2))

        self.fitness = displacement




    @trollius.coroutine
    def update(self, world, logging_callback=None):
        old_state = self.state_switch.get_current_state()
        state = self.state_switch.update(world.get_world_time())

        # if old_state != state:
        #     print('state: {0}, time = {1}, fitness = {2}'.format(state, world.get_world_time(), self.get_fitness()))

        if state == 'warmup':
            self.reset_fitness()

        elif state == 'evaluate':
            self.update_fitness()

        elif state == 'next_brain':

            print("Evaluation over")
            print("%%%%%%%%%%%%%%%%%%\n\nEvaluated {0} brains".format(str(self.total_brains_evaluated+1)))
            print("queue length = {0}".format(len(self.evaluation_queue)))
            print("distance covered: {0}".format(self.fitness ))
            print("evaluation time was {0}s\n\n%%%%%%%%%%%%%%%%%%".format(self.evaluation_time_actual))

            self.fitness_buffer.append(self.fitness / self.evaluation_time_actual)


            # # set another drive direction
            # yield From(world.set_drive_direction(0.5, 0.75, 0.))


            # if repeated brain evaluation is not over
            if len(self.fitness_buffer) < self.repeat_evaluations:

                # continue evaluating the same brain:
                next_brain = self.active_brain

            # if repeated brain evaluation is over
            else:
                yield From(wait_for(world.pause(True)))

                aver_fitness = sum(self.fitness_buffer) / float(len(self.fitness_buffer))
                self.brain_velocity[self.active_brain] = aver_fitness

                print("Brain evaluations are over, average result = {0} ".format(aver_fitness))


                # if all brains are evaluated, produce new generation:
                if len(self.evaluation_queue) == 0:

                    self.evaluation_queue = \
                        deque(self.evolution.produce_new_generation(self.brain_velocity.items()))

                    # do logging stuff
                    if logging_callback:
                        self.exec_logging_callback(logging_callback, self.brain_velocity.items())

                    self.brain_velocity.clear()
                    self.generation_number += 1
                    print("GENERATION #{}".format(self.generation_number))



                # continue evaluating brains from the queue:
                next_brain = self.evaluation_queue[0]

            # make snapshot (disable when learning is online, crashes only happen when offline):
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



    def parameter_string(self):
        out = ""
        out += "population size      set to {0}\n".format(self.evolution.pop_size)
        out += "tournament size      set to {0}\n".format(self.evolution.tournament_size)
        out += "elite size           set to {0}\n".format(self.evolution.elite_size)
        out += "speciation threshold set to {0}\n".format(self.evolution.speciation_threshold)
        out += "evaluation time      set to {0}\n".format(self.evaluation_time)
        out += "warmup  time         set to {0}\n".format(self.warmup_time)
        out += "evaluation repeats   set to {0}\n".format(self.repeat_evaluations)
        out += "max number of generations set to {0}\n".format(self.max_generations)
        out += "asexual reproduction: {0}\n".format(self.asexual)
        return out





#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
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




#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
from pygazebo.msg.request_pb2 import Request

class RobotLearnerOnlineRefac(RobotLearnerOnline):

    def __init__(self, world, robot, insert_position, body_spec, brain_spec, mutator, conf):
        self.finished = False
        self.eval_over = False
        RobotLearnerOnline.__init__(self, world, robot, insert_position,
                                    body_spec, brain_spec, mutator, conf)



    @trollius.coroutine
    def initialize(self, world, init_genotypes=None):
        yield From(RobotLearnerOnline.initialize(self, world, init_genotypes))

        self.fitness_subscr = (
            world.manager.subscribe(
                topic_name='/gazebo/default/{0}/fitness'.format(self.robot.name),
                msg_type='gazebo.msgs.Request',
                callback=self.fitness_evaluated_callback
            )
        )
        yield From(self.fitness_subscr.wait_for_connection())


    def fitness_evaluated_callback(self, data):
        msg = Request()
        msg.ParseFromString(data)
        fitness = msg.dbl_data

        self.brain_velocity[self.active_brain] = fitness
        self.eval_over = True



    @trollius.coroutine
    def update(self, world, logging_callback=None):
        if self.eval_over:
            # pause world
            yield From(wait_for(world.pause(True)))

            # output info to console
            logger.info("{}/{} : fitness = {:.7f}".format(
                self.total_brains_evaluated+1,
                len(self.evaluation_queue),
                self.brain_velocity[self.active_brain]))

            # if all brains are evaluated, produce new generation:
            if len(self.evaluation_queue) == 0:

                self.evaluation_queue = \
                    deque(self.evolution.produce_new_generation(self.brain_velocity.items()))

                # do logging stuff
                if logging_callback:
                    self.exec_logging_callback(logging_callback, self.brain_velocity.items())

                self.brain_velocity.clear()
                self.generation_number += 1
                logger.info("GENERATION #{}".format(self.generation_number))


            next_brain = self.evaluation_queue[0]
            yield From(self.activate_brain(world, next_brain))

            # # make snapshot (disable when learning is online, crashes only happen when offline):
            # yield From(world.create_snapshot())
            # -----------------------------------------------------------------------------------
            # if we are past this line, the simulator did not crash while inserting a new brain
            # -----------------------------------------------------------------------------------
            self.eval_over = False
            self.evaluation_queue.popleft()
            self.total_brains_evaluated += 1
            if self.generation_number >= self.max_generations: self.finished = True

        raise Return(self.finished)




#### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### #### ####
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