import warnings
warnings.filterwarnings("ignore")

import climt
from sympl import (
    PlotFunctionMonitor, NetCDFMonitor,
    TimeDifferencingWrapper, get_constant
)
import numpy as np
from datetime import timedelta
import pickle
import time
import matplotlib.pyplot as plt
import mgzip

def save_state(state, core, filename):
    
    spec = core._gfs_cython.get_spectral_arrays()

    with mgzip.open(filename, 'wb') as f:
        pickle.dump([state,spec], f)

#to perturb the log surface pressure spectral array
def perturb(X):
    X=np.array(X)
    N=np.random.uniform(-1,1,np.shape(X[4]))*np.sqrt(2)*10**-4
    X[4][:]=(X[4]+N)[:]

#load state from memory
def load_state(state, core, filename):
    
    with mgzip.open(filename, 'rb') as f:
        fields, spec = pickle.load(f)
    
    if pert_flag:
        perturb(spec)
        core.set_flag(False)
    core._gfs_cython.reinit_spectral_arrays(spec)
    
    state.update(fields)


pert_flag=0

import os
import sys

k_val=int(sys.argv[1])

climt.set_constants_from_dict({
    'stellar_irradiance': {'value': 200, 'units': 'W m^-2'}})

model_time_step = timedelta(minutes=20)

# Create components
convection = climt.EmanuelConvection()
boundary=TimeDifferencingWrapper(climt.SimpleBoundaryLayer(scaling_land=0.5))
radiation = climt.GrayLongwaveRadiation()
slab_surface = climt.SlabSurface()

dycore = climt.GFSDynamicalCore(
    [boundary,radiation, slab_surface,
    convection], number_of_damped_levels=5
)

grid = climt.get_grid(nx=128, ny=62)

# Create model state
my_state = climt.get_default_state([dycore], grid_state=grid)
dycore(my_state, model_time_step)

load_state(my_state, dycore, 'spinup_2year')
 

# setup fields to save

Air_temp=[]
Time=[]
Longitude=my_state['longitude'].values[:]
Latitude=my_state['latitude'].values[:]
Area_type=my_state['area_type']

for i in range(26280):#26280 one year
    
    if i==1:
        dycore.set_flag(True)

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step

    # if (i+1)%720==0:
    #     n=int((i+1)/720)
    #     save_state(my_state, dycore, '../initial/state'+str(n))

    #saving fields
    if (i+1)%18==0:
        Air_temp.append(my_state['air_temperature'].values[0])
        Time.append(my_state['time'])

    if (i+1)%26280==0:
        n=int((i+1)/26280)
        with mgzip.open('../long_run_temp/temp_year'+str(n), 'wb') as f:
            pickle.dump([Air_temp,Time,Longitude,Latitude,Area_type], f)
        
        Air_temp=[]
        Time=[]
