import pickle
import numpy as np
import os

# get passed arguments
import sys
dir=str(sys.argv[1])

with open(dir+'/config', 'rb') as f:
    config = pickle.load(f)

k=config[0]/365
Num_traj=config[1]
tau=config[2]
Ta=config[3]


# get trajectory data and R_log from file

with open(dir+'/T', 'rb') as f:
    T = pickle.load(f)

with open(dir+'/R_log', 'rb') as f:
    R = pickle.load(f)


# calculate probability for trajectory
lamb=R/Ta
p=np.ones(Num_traj)

for i in range(Num_traj):

    p[i]=(1/Num_traj)*(np.exp(Ta*lamb-k*np.array(T[i]).mean()*Ta))


# remove unnecessary files
for e in range(Num_traj):
    os.remove(dir+'/A'+str(e+1))

for e in range(Num_traj):
    os.remove(dir+'/traj'+str(e+1))

# write probability file
with open(dir+'/prob', 'wb') as f:
    pickle.dump(p, f)

# pass_wrap indicates completion of the script
with open(dir+'/pass_wrap', 'wb') as f:
    pickle.dump([], f)


