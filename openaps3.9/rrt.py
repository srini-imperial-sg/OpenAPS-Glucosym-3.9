#!/usr/bin/env python
# coding: utf-8

# ### Semantic RRT
# 
# RRT* with semantic state boundaries.

# In[10]:


import numpy as np
import random
import matplotlib.pyplot as plt
import os
import networkx as nx
import time


# In[11]:


def find_filenames (path, name_filter='patientA', suffix=".csv"):
    fileset = []
    
    for root, dirs, files in os.walk(path):
        for file in files:
                if file.endswith(suffix) and name_filter in file:
                        fileresult = os.path.join(root, file)
                        fileset.append(fileresult)
    return fileset


# O(n^2) implementation of RRT*
# Builds more efficient paths than RRT, and includes a more general definition of cost that we could exploit
# max_len constrains maximum path length to within a given deadline
def rrt_star(x0, num_iter, delta, prev_state, max_len=None, return_path=True, constraints=[True,[-5, -10],[3, 10],[-2.5, -5],[2.5, 5]]):
    
    x0 = (x0[0], x0[1])
    G = nx.Graph()
    G.add_node(x0, parent=prev_state)

    cost = {x0:0.}
    pathLength = {x0:0}
    ball = not isinstance(delta, list)

    safe_nodes = {}
    t_conv = 0 #convergence time
    check_num = 2 #check both 1st and 2nd deriv
    
#     for ni in range(1, num_iter+1):
    ni = 0 
    while ni <= num_iter:
        ni = ni + 1 #update step number
        if ni==num_iter and len(safe_nodes) == 0 and constraints[0]:
            if num_iter < 50000:
                if len(G.nodes)<2:
                    check_num = 1 #check only 1st 
                    ni = 1 # reset
                    print("reset ni")
                else:
                    num_iter += 5000 #try 1000 steps more 
                    print ("add num_iter,",num_iter)

    
        xrand = (random.uniform(70, 180), 100*random.uniform(-1.5, 2))
        xnearest = nearest_star(G, xrand, pathLength, max_len)
        xnew = extend_star(xrand, xnearest, delta)

        
        if len(G.nodes)>1:
            check_num = 2 #check both 1st and 2nd deriv

        if not validConnection(xnew, xnearest, G.nodes[xnearest]['parent'], constraints,check_num=check_num) or xnearest in safe_nodes:
#             print("invalid vertex:",xnew, xnearest, G.nodes[xnearest]['parent'])
            continue

        Xnear = near(G, xnew, r=delta+1) #
#         Xnear = near(G, xnearest, delta)

        xmin = xnearest
        cmin = cost[xnearest] + line_cost(xnearest, xnew)
        
        # connect new node along minimum cost (distance) path
        for xnear in Xnear:
            if validConnection(xnew, xnear, G.nodes[xnear]['parent'], constraints,check_num=check_num) or xnear in safe_nodes:
                c = cost[xnear] + line_cost(xnear, xnew)
                if c < cmin:
                    xmin = xnear
                    cmin = c
        
        G.add_node(xnew, parent=xmin)
        G.add_edge(xmin, xnew) # add xnew to tree
        cost[xnew] = cmin
        pathLength[xnew] = pathLength[xmin] + 1

        # rewire the tree
        for xnear in Xnear:
            if validConnection(xnear, xnew, G.nodes[xnew]['parent'], constraints,check_num=check_num):
                c = cost[xnew] + line_cost(xnew, xnear)
                if c < cost[xnear]:
                    xparent = G.nodes[xnear]['parent']
                    G.remove_edge(xparent, xnear)
                    G.add_edge(xnew, xnear)
                    G.nodes[xnear]['parent'] = xnew
                    cost[xnear] = c
                    pathLength[xnear] = pathLength[xnew] + 1
                
        # check if new node is in a safe region
        if xnew[0] < 140 and xnew[0] > 120:# and xnew[1]<100 and xnew[1]>0:
            safe_nodes[xnew] = True
            if t_conv == 0:
                t_conv = ni
                
    if len(safe_nodes) == 0:
        print('No path found to safety')
        return [],G,t_conv
    else:
        print(len(safe_nodes), 'safe nodes found')
    
    if return_path:
        # calculate cost of each path found
        mincost, minpath = np.inf, []
        for u in safe_nodes.keys():
            path = nx.shortest_path(G, source=x0, target=u)

            safety, bg_smooth, iob_smooth = 0, 0, 0
            for i in range(1, len(path)):
                safety += risk(path[i][0])
                bg_smooth += np.abs(path[i][0] - path[i-1][0])
                iob_smooth += np.abs(path[i][1] - path[i-1][1])

            cost = safety+bg_smooth+iob_smooth
            if cost < mincost:
                mincost=cost
                minpath=path
#             print('Length', len(path), 'cost', cost, 'subcategories', safety, bg_smooth, iob_smooth)
        
        return minpath, G, t_conv
    else:
        return safe_nodes, G, t_conv




# return the node in G nearest to given node v based on L2 norm
# O(n) time
def nearest_star(G, v, pathLength, max_len):
    vnear = None
    mindist = np.inf

    for u in G.nodes:
        if max_len is not None:
            if pathLength[u] >= max_len:
                continue
        d = np.linalg.norm(np.asarray(u) - np.asarray(v))

        if d < mindist:
            mindist = d
            vnear = u
    
    return vnear

# create new node from vnear towards vrand 
# @param variable: toggles between fixed and variable step
def extend_star(vrand, vnear, delta):
    dir = np.asarray(vrand) - np.asarray(vnear) # direction from near to rand
    if np.linalg.norm(dir) < delta:
        return vrand

    dir = (dir / np.linalg.norm(dir)) * delta # normalize to length delta
    vnew = (vnear[0] + dir[0], vnear[1] + dir[1])
    return vnew

# find all nodes in G.V that are within a ball of radius r of node x
# O(n) time
def near(G, x, r):
    V = []

    for u in G.nodes:
        d = np.linalg.norm(np.array(u) - np.array(x))

        if d <= r:
            V.append(u)
    
    return V

# cost of x -> y
def line_cost(x, y):
    return np.linalg.norm(np.array(y) - np.array(x))

#check_num=1: only check 1st deriv
#check_num=2: check 1st and 2nd deriv
def validConnection(xnew, xi, xparent, constraints=None,check_num=2):
    if not constraints[0]:
        return True
    D = np.array(xnew) - np.array(xi)
    E = np.array(xnew) - 2*np.array(xi) + np.array(xparent)

    # Constraints; keep in mind IOB is multiplied by 100
    # constrains = [True, [dbg_low, diob_low], [dbg_high, diob_high], [d2bg_low, d2iob_low], [d2bg_high, d2iob_high]]
    deltaL = np.array(constraints[1]) # 1st deriv. lower bound
    deltaU = np.array(constraints[2]) # 1st deriv. upper bound
    etaL = np.array(constraints[3]) # 2nd deriv. LB
    etaU = np.array(constraints[4]) # 2nd deriv. UP

    if np.any([deltaL > D, deltaU < D]): #violate 1st deriv
        return False    
    else:
        if check_num>1 and np.any([etaL > E, etaU < E]):#violate 2nd deriv
            return False
        else:
            return True

# returns BG risk index
def risk(bg):
    f = np.power(np.log(bg), 1.084) - 5.381
    ri = 22.77*np.power(f, 2)
    return ri


# In[19]:




if __name__=="__main__":

    path, T, t_conv = rrt_star(x0, 3000, delta=5, prev_state=prev_state)
    path_nc, T_nc, t_conv_nc = rrt_star(x0, 800, delta=5, prev_state=prev_state, constraints=[False])
