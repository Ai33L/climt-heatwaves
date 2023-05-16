import warnings
warnings.filterwarnings("ignore")

import climt
from sympl import (TimeDifferencingWrapper)
import numpy as np
from datetime import timedelta
import pickle
import gzip
import matplotlib.pyplot as plt
import os

os.chdir(os.getcwd())

# Function to perturb spectral surface pressure array
def perturb(X):
    X=np.array(X)
    N=np.random.uniform(-1,1,np.shape(X[4]))*np.sqrt(2)*10**-4
    X[4][:]=(X[4]+N)[:]

pert_flag=1

# load state from memory, perturb if pert_flag is true 
def load_state(state, core, filename):
        
    with gzip.open(filename, 'rb') as f:
        fields, spec = pickle.load(f)
    
    if pert_flag:
        core.set_flag(False)
        perturb(spec)

    core._gfs_cython.reinit_spectral_arrays(spec)    
    state.update(fields)

with gzip.open('obs_mask', 'rb') as f:
    obs_mask = pickle.load(f)

# Function to calculate the observable
def Obs(state):
    lat = np.radians(state['latitude'].values[:])
    O=state['air_temperature'][0].values[:]
    return((O*np.cos(lat)*obs_mask).sum())/((np.cos(lat)*obs_mask).sum())

# Function to simulate a trajectory
def traj():

    model_time_step = timedelta(minutes=20)

    convection = climt.EmanuelConvection()
    boundary=TimeDifferencingWrapper(climt.SimpleBoundaryLayer(scaling_land=0.7))
    radiation = climt.GrayLongwaveRadiation()
    slab_surface = climt.SlabSurface()
    optical_depth = climt.Frierson06LongwaveOpticalDepth(linear_optical_depth_parameter=1, longwave_optical_depth_at_equator=6)

    dycore = climt.GFSDynamicalCore(
        [boundary ,radiation, convection, slab_surface], number_of_damped_levels=5
    )

    grid = climt.get_grid(nx=128, ny=64)

    my_state = climt.get_default_state([dycore], grid_state=grid)
    dycore(my_state, model_time_step)

    load_state(my_state, dycore, 'spinup_3yr')

    A=[]

    for i in range(72*150):#26280 one year

        if i==1:
            dycore.set_flag(True)

        diag, my_state = dycore(my_state, model_time_step)
        my_state.update(diag)
        my_state['time'] += model_time_step

        A.append(Obs(my_state))

    return A

# Section to run the simulation of trajectories

# T=[]
# num_of_trajs=30
# for k in range(num_of_trajs):

#     print('Trajectory', k+1)
#     x=traj()
#     T.append(x)

# with gzip.open('lyapunov_data', 'wb') as f:
#     pickle.dump(T, f)

# Section to analyse the trajectory data

def diff(m):
    sum=0
    c=0
    for i in range(len(m)):
        for j in range(i,len(m)):
            sum+=np.abs(m[i]-m[j])
            c+=1
    return sum/c

def lyap(A):

    L=[]
    for i in range(len(A[0])):
        pts=[]
        for j in range(30):
            pts.append(A[j][i])
        
        L.append(diff(pts))
    
    return L

with gzip.open('lyapunov_data', 'rb') as f:
    T=pickle.load(f)

for e in T:
    plt.plot(np.array(range(len(e)))/(3*24), e)
plt.show()

ly=lyap(T)
plt.plot(np.array(range(len(T[0])))/(3*24),ly)
plt.yscale('log')
# plt.semilogy(basey=2)
plt.xlabel('Time (days)')
plt.ylabel('Average distance between runs (K)')
plt.grid()
plt.savefig('lyapunov.pdf', bbox_inches='tight')
plt.show()
