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
from .robot_learner import RobotLearner
from ..util import StateSwitch, rotate_vertical




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
        pso_temp = conf.pso_temperature

        # particle swarm optimizer:
        self.pso = PSOptimizer(individual_coef=loc_coef, social_coef=glob_coef, temperature=pso_temp)


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
    def __init__(self, individual_coef, social_coef, temperature):
        self.ind_coef = individual_coef
        self.social_coef = social_coef
        self.temperature = temperature

    def step(self, ind_best, global_best, current_pos, velocity):
        new_pos = [0 for _ in range(len(ind_best))]

        for i in range(len(new_pos)):
            accel = random.gauss(1.0, self.temperature) * self.ind_coef * (ind_best[i] - current_pos[i]) + \
                    random.gauss(1.0, self.temperature) * self.social_coef * (global_best[i] - current_pos[i])

            # accel = self.ind_coef * ( random.gauss(1.0, self.temperature)*ind_best[i] - current_pos[i] ) + \
            #         self.social_coef * ( random.gauss(1.0, self.temperature)*global_best[i] - current_pos[i] )

            velocity[i] += accel

        for i in range(len(new_pos)):
            new_pos[i] = current_pos[i] + velocity[i]

        return new_pos