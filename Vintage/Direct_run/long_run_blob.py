# Slurm script to run the model for chunks of time (around 25 years)
# To be run multiple times and combined

import warnings
warnings.filterwarnings("ignore")

import climt
from sympl import (TimeDifferencingWrapper)
import numpy as np
from datetime import timedelta
import pickle
import time
import gzip
import xarray as xr
import zarr

import sys
key=int(sys.argv[1])

pert_flag=1

# Function to perturb spectral surface pressure array
def perturb(X):
    X=np.array(X)
    N=np.random.uniform(-1,1,np.shape(X[4]))*np.sqrt(2)*10**-4
    X[4][:]=(X[4]+N)[:]

#load state from memory
def load_state(state, core, filename):
        
    with gzip.open(filename, 'rb') as f:
        fields, spec = pickle.load(f)
        
    if pert_flag:
        core.set_flag(False)
        perturb(spec)

    core._gfs_cython.reinit_spectral_arrays(spec)    
    state.update(fields)

model_time_step = timedelta(minutes=20)

# Create components
convection = climt.EmanuelConvection()
boundary=TimeDifferencingWrapper(climt.SimpleBoundaryLayer(scaling_land=0.7))
radiation = climt.GrayLongwaveRadiation()
slab_surface = climt.SlabSurface()
optical_depth = climt.Frierson06LongwaveOpticalDepth(linear_optical_depth_parameter=1, longwave_optical_depth_at_equator=6)

dycore = climt.GFSDynamicalCore(
    [boundary ,radiation, convection, slab_surface], number_of_damped_levels=5
)

grid = climt.get_grid(nx=128, ny=64)

# Create model state
my_state = climt.get_default_state([dycore], grid_state=grid)
dycore(my_state, model_time_step)

load_state(my_state, dycore, 'spinup_3yr')


# Run model for a year after initialisation
for i in range(26280):#26280 one year

    if i==1:
        dycore.set_flag(True)

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step


# Function to format climate model output
def format_data(state):
    arr=[]
    for i in state.keys():
        if i!='time':
            if i in ['air_temperature','air_pressure','specific_humidity',
            'northward_wind','eastward_wind','surface_air_pressure', 'surface_temperature',
            'surface_upward_latent_heat_flux', 'surface_upward_sensible_heat_flux',
            'boundary_layer_height', 'divergence_of_wind','upwelling_longwave_flux_in_air',
            'downwelling_longwave_flux_in_air']:
                if i in ['upwelling_longwave_flux_in_air','downwelling_longwave_flux_in_air']:
                    arr.append(state[i][0].rename('surface_'+i).astype('float32'))    
                else:
                    arr.append(state[i].rename(i).astype('float32'))

    data=xr.merge(arr)
    data = data.expand_dims(time=[my_state['time']])

    return(data)

# store common data before model start
arr_common=[]
for i in ['longitude','latitude','area_type']:
    arr_common.append(my_state[i].rename(i))
store = zarr.storage.DirectoryStore("long_run/common")
data_common=xr.merge(arr_common) 
data_common.to_zarr(store=store, mode='w')

data_flag=0
index=1

# Run model for 25 years and store data
for i in range(26280*25):#26280 one year
    
    if (i+1)%18==0:
        if data_flag==0:
            Data=format_data(my_state)
            data_flag=1
        else:
            Data=xr.combine_by_coords([Data,format_data(my_state)])
    
    if (i+1)%26280==0:
        data_flag=0
        compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
        enc = {x: {"compressor": compressor} for x in Data}

        store = zarr.storage.DirectoryStore("long_run/run"+str(key)+"/year"+str(index)) 
        (Data.resample(time='1D').mean()).to_zarr(store=store, encoding=enc, mode='w')
        index=index+1

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step