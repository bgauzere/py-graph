#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 16:03:11 2019

pre-image
@author: ljia
"""

import sys
import numpy as np
import multiprocessing
from tqdm import tqdm
import networkx as nx
import matplotlib.pyplot as plt


sys.path.insert(0, "../")
from pygraph.kernels.marginalizedKernel import marginalizedkernel
from pygraph.utils.graphfiles import loadDataset


ds = {'name': 'MUTAG', 'dataset': '../datasets/MUTAG/MUTAG.mat',
          'extra_params': {'am_sp_al_nl_el': [0, 0, 3, 1, 2]}}  # node/edge symb

DN, y_all = loadDataset(ds['dataset'], extra_params=ds['extra_params'])
DN = DN[0:10]

lmbda = 0.03 # termination probalility
r_max = 10 # recursions
l = 500
alpha_range = np.linspace(0.1, 0.9, 9)
k = 5 # k nearest neighbors

# randomly select two molecules
np.random.seed(1)
idx1, idx2 = np.random.randint(0, len(DN), 2)
g1 = DN[idx1]
g2 = DN[idx2]

# compute 
k_list = [] # kernel between each graph and itself.
k_g1_list = [] # kernel between each graph and g1
k_g2_list = [] # kernel between each graph and g2
for ig, g in tqdm(enumerate(DN), desc='computing self kernels', file=sys.stdout): 
    ktemp = marginalizedkernel([g, g1, g2], node_label='atom', edge_label=None,
                               p_quit=lmbda, n_iteration=20, remove_totters=False,
                               n_jobs=multiprocessing.cpu_count(), verbose=False)
    k_list.append(ktemp[0][0, 0])
    k_g1_list.append(ktemp[0][0, 1])
    k_g2_list.append(ktemp[0][0, 2])

g_best = []
dis_best = []
# for each alpha
for alpha in alpha_range:
    print('alpha =', alpha)
    # compute k nearest neighbors of phi in DN.
    dis_list = [] # distance between g_star and each graph.
    for ig, g in tqdm(enumerate(DN), desc='computing distances', file=sys.stdout):
        dtemp = k_list[ig] - 2 * (alpha * k_g1_list[ig] + (1 - alpha) * 
                      k_g2_list[ig]) + (alpha * alpha * k_list[idx1] + alpha * 
                      (1 - alpha) * k_g2_list[idx1] + (1 - alpha) * alpha * 
                      k_g1_list[idx2] + (1 - alpha) * (1 - alpha) * k_list[idx2])
        dis_list.append(dtemp)
    
    # sort
    sort_idx = np.argsort(dis_list)
    dis_gs = [dis_list[idis] for idis in sort_idx[0:k]]
    g0hat = DN[sort_idx[0]] # the nearest neighbor of phi in DN
    if dis_gs[0] == 0: # the exact pre-image.
        print('The exact pre-image is found from the input dataset.')
        g_pimg = g0hat
        break
    dhat = dis_gs[0] # the nearest distance
    Dk = [DN[ig] for ig in sort_idx[0:k]] # the k nearest neighbors
    gihat_list = []
    
    i = 1
    r = 1
    while r < r_max:
        print('r =', r)
        found = False
        for ig, gs in enumerate(Dk + gihat_list):
#            nx.draw_networkx(gs)
#            plt.show()
            fdgs = int(np.abs(np.ceil(np.log(alpha * dis_gs[ig])))) # @todo ???             
            for trail in tqdm(range(0, l), desc='l loop', file=sys.stdout):
                # add and delete edges.
                gtemp = gs.copy()
                np.random.seed()
                # which edges to change.
                idx_change = np.random.randint(0, nx.number_of_nodes(gs) * 
                                               (nx.number_of_nodes(gs) - 1), fdgs)
                for item in idx_change:
                    node1 = int(item / (nx.number_of_nodes(gs) - 1))
                    node2 = (item - node1 * (nx.number_of_nodes(gs) - 1))
                    if node2 >= node1:
                        node2 += 1
                    # @todo: is the randomness correct?
                    if not gtemp.has_edge(node1, node2):
                        gtemp.add_edges_from([(node1, node2, {'bond_type': 0})])
#                        nx.draw_networkx(gs)
#                        plt.show()
#                        nx.draw_networkx(gtemp)
#                        plt.show()
                    else:
                        gtemp.remove_edge(node1, node2)
#                        nx.draw_networkx(gs)
#                        plt.show()
#                        nx.draw_networkx(gtemp)
#                        plt.show()
#                nx.draw_networkx(gtemp)
#                plt.show()
                
                # compute distance between phi and the new generated graph.
                knew = marginalizedkernel([gtemp, g1, g2], node_label='atom', edge_label=None,
                               p_quit=lmbda, n_iteration=20, remove_totters=False,
                               n_jobs=multiprocessing.cpu_count(), verbose=False)
                dnew = knew[0][0, 0] - 2 * (alpha * knew[0][0, 1] + (1 - alpha) * 
                      knew[0][0, 2]) + (alpha * alpha * k_list[idx1] + alpha * 
                      (1 - alpha) * k_g2_list[idx1] + (1 - alpha) * alpha * 
                      k_g1_list[idx2] + (1 - alpha) * (1 - alpha) * k_list[idx2])
                if dnew <= dhat: # the new distance is smaller
                    print('I am smaller!')
                    dhat = dnew
                    gnew = gtemp.copy()
                    found = True # found better graph.
                    r = 0
        if found:
            gihat_list = [gnew]
            dis_gs.append(dhat)
        else:
            r += 1
    dis_best.append(dhat)
    g_best += ([g0hat] if len(gihat_list) == 0 else gihat_list)    

for idx, item in enumerate(alpha_range):
    print('when alpha is', item, 'the shortest distance is', dis_best[idx])
    print('the corresponding pre-image is')
    nx.draw_networkx(g_best[idx])
    plt.show()