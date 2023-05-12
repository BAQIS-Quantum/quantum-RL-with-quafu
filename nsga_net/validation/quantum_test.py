import argparse
import logging
import os
import sys
# sys.path.insert(0, ' ')
import time
from functools import reduce

import cirq
import gym
# model imports
import models.quantum_genotypes as genotypes
import numpy as np
import tensorflow as tf
from misc import utils
from models.quantum_models import generate_circuit
from models.quantum_models import generate_model_policy as Network
from models.quantum_models import get_model_circuit_params
from search.quantum_train_search import compute_returns, gather_episodes
from sympy import im
from visualization.qrl import get_obs_policy, get_quafu_exp

parser = argparse.ArgumentParser('Quantum RL Inference')
parser.add_argument('--save', type=str, default='qEXP_quafu', help='experiment name')
parser.add_argument('--batch_size', type=int, default=1, help='batch size')
parser.add_argument('--infer_episodes', type=int, default=100, help='the number of infer episodes')
parser.add_argument('--gamma', type=float, default=1.0, help='discount parameter')
parser.add_argument('--env_name', type=str, default="CartPole-v1", help='environment name')
parser.add_argument('--state_bounds', type=np.array, default=np.array([2.4, 2.5, 0.21, 2.5]), help='state bounds')
parser.add_argument('--n_qubits', type=int, default=4, help='the number of qubits')
parser.add_argument('--n_actions', type=int, default=2, help='the number of actions')
parser.add_argument('--arch', type=str, default='NSGANet_id10', help='which architecture to use')
parser.add_argument('--model_path', type=str, default='./weights/weights_id10_quafu_94.h5', help='path of pretrained model')
parser.add_argument('--beta', type=float, default=1.0, help='output parameter')

args = parser.parse_args(args=[])
args.save = 'infer-{}-{}'.format(args.save, time.strftime("%Y%m%d-%H%M%S"))
utils.create_exp_dir(args.save)

log_format = '%(asctime)s %(message)s'
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format=log_format, datefmt='%m/%d %I:%M:%S %p')
fh = logging.FileHandler(os.path.join(args.save, 'log.txt'))
fh.setFormatter(logging.Formatter(log_format))
logging.getLogger().addHandler(fh)

qubits = cirq.GridQubit.rect(1, args.n_qubits)
genotype = eval("genotypes.%s" % args.arch)
ops = [cirq.Z(q) for q in qubits]
observables = [reduce((lambda x, y: x * y), ops)] # Z_0*Z_1*Z_2*Z_3


def main():
    logging.info("args = %s", args)

    model = Network(qubits, genotype, args.n_actions, observables)

    model.load_weights(args.model_path)
    
    # inference 
    valid_reward = infer(model)


def infer(model):
    episode_reward_history = []
    for batch in range(args.infer_episodes // args.batch_size):
        # Gather episodes
        tasklist, episodes = gather_episodes(args.state_bounds, args.n_actions, model, args.batch_size, 
                                              args.env_name, args.beta, qubits, genotype)
        logging.info(tasklist)

        # Group states, actions and returns in numpy arrays
        states = np.concatenate([ep['states'] for ep in episodes])
        actions = np.concatenate([ep['actions'] for ep in episodes])
        rewards = [ep['rewards'] for ep in episodes]

        # Store collected rewards
        for ep_rwds in rewards:
            episode_reward_history.append(np.sum(ep_rwds))

        # avg_rewards = np.mean(episode_reward_history[-10:])

        logging.info('valid finished episode: %f', (batch + 1) * args.batch_size)
        logging.info('valid average rewards: %f', episode_reward_history[-1])
    
        if episode_reward_history[-1] >= 200.0:
            break
    return episode_reward_history


if __name__ == '__main__':
    main()