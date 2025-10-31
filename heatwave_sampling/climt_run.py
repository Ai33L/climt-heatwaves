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

# sets perturbation of loaded state
pert_flag=1

# Function to perturb spectral surface pressure array
def perturb(X):
    X=np.array(X)
    N=np.random.uniform(-1,1,np.shape(X[4]))*np.sqrt(2)*10**-4
    X[4][:]=(X[4]+N)[:]

# function to load state from memory
def load_state(state, core, filename):
        
    with gzip.open(filename, 'rb') as f:
        fields, spec = pickle.load(f)
        
    if pert_flag:
        core.set_flag(False)
        perturb(spec)

    core._gfs_cython.reinit_spectral_arrays(spec)    
    state.update(fields)

# sets model timestep
model_time_step = timedelta(minutes=20)

# Model creation
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


# loads model state from file --> provide full path to spinup_3yr if the code cannot find it
load_state(my_state, dycore, 'spinup_3yr')


# Run model for a year after initialisation -- skipping for now
#for i in range(26280):#26280 one year
#
#    if i==1:
#        dycore.set_flag(True)
#
#    diag, my_state = dycore(my_state, model_time_step)
#    my_state.update(diag)
#    my_state['time'] += model_time_step


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

    # sets lat-lon coordinates
    lats=state['latitude'].values[:,0]; lons=state['longitude'].values[0,:]
    data=data.assign_coords({"lat": lats, 'lon': lons})
    
    data = data.expand_dims(time=[my_state['time']])

    return(data)

data_flag=0
index=1

# Run model for 10 days and store data
for i in range(720):#26280 one year
    
    if (i+1)%18==0:
        if data_flag==0:
            Data=format_data(my_state)
            data_flag=1
        else:
            Data=xr.combine_by_coords([Data,format_data(my_state)])
    
    if (i+1)%72==0:
        print('day', index)
        index=index+1

    if (i+1)%720==0:
        data_flag=0
        compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
        enc = {x: {"compressor": compressor} for x in Data}

        store = zarr.storage.DirectoryStore("climt_run/run_data") 
        (Data.resample(time='1D').mean()).to_zarr(store=store, encoding=enc, mode='w')

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step
