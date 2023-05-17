import warnings
warnings.filterwarnings("ignore")

import climt
from sympl import (TimeDifferencingWrapper)
import numpy as np
from datetime import timedelta
import pickle
import gzip
import zarr
import xarray as xr


# get passed arguments
import sys
traj_num=int(sys.argv[1])
iter=int(sys.argv[2])
dir=str(sys.argv[3])
with gzip.open(dir+'/pert_flag', 'rb') as f:
    pert_flag = int(pickle.load(f)[traj_num-1])


# get tau value
with gzip.open(dir+'/config', 'rb') as f:
    config = pickle.load(f)

tau=config[2]
soil_conf=config[4]


# Function to perturb spectral surface pressure array - To introduce perturbation in model
def perturb(X):
    X=np.array(X)
    N=np.random.uniform(-1,1,np.shape(X[4]))*np.sqrt(2)*10**-4
    X[4][:]=(X[4]+N)[:]


#load state from memory - perturb if pert_flag is true
def load_state(state, core, filename):
        
    with gzip.open(filename, 'rb') as f:
        fields, spec = pickle.load(f)
    if pert_flag:
        core.set_flag(False)
        perturb(spec)

    core._gfs_cython.reinit_spectral_arrays(spec)    
    state.update(fields)

# function to save state
def save_state(state, core, filename):
    
    spec = core._gfs_cython.get_spectral_arrays()

    with gzip.open(filename, 'wb') as f:
        pickle.dump([state,spec], f)


# trajectory simulation
def Traj():

    model_time_step = timedelta(minutes=20)

    convection = climt.EmanuelConvection()
    boundary=TimeDifferencingWrapper(climt.SimpleBoundaryLayer(scaling_land=soil_conf))
    radiation = climt.GrayLongwaveRadiation()
    slab_surface = climt.SlabSurface()

    dycore = climt.GFSDynamicalCore(
        [boundary ,radiation, convection, slab_surface], number_of_damped_levels=5
    )

    grid = climt.get_grid(nx=128, ny=64)

    my_state = climt.get_default_state([dycore], grid_state=grid)
    dycore(my_state, model_time_step)

    load_state(my_state, dycore, dir+'/traj'+str(traj_num))

    with gzip.open('obs_mask', 'rb') as f:
            obs_mask = pickle.load(f)

    def Obs(state):
        lat = np.radians(my_state['latitude'].values[:])
        O=state['air_temperature'][0].values[:]
        return((O*np.cos(lat)*obs_mask).sum())/((np.cos(lat)*obs_mask).sum())

    A=[] # to store observable

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

    # store common data
    arr_common=[]
    for i in ['longitude','latitude','area_type']:
        arr_common.append(my_state[i].rename(i))
    store = zarr.storage.DirectoryStore(dir+'/common')
    data_common=xr.merge(arr_common) 
    #data_common.to_zarr(store=store, mode='w')

    data_flag=0
    for i in range(72*tau):#26280 one year

        A.append(Obs(my_state))

        if i==1:
            dycore.set_flag(True)

        if (i+1)%18==0:
            if data_flag==0:
                Data=format_data(my_state)
                data_flag=1
            else:
                Data=xr.combine_by_coords([Data,format_data(my_state)])
        
        if (i+1)%(72*tau)==0:
            compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
            enc = {x: {"compressor": compressor} for x in Data}

            store = zarr.storage.DirectoryStore(dir+'/data_'+str(iter)+'_'+str(traj_num)) 
            (Data.resample(time='1D').mean()).to_zarr(store=store, encoding=enc, mode='w')

            save_state(my_state, dycore, dir+'/traj_new'+str(traj_num))

            with gzip.open(dir+'/A'+str(traj_num), 'wb') as f:
                pickle.dump(A, f)

        diag, my_state = dycore(my_state, model_time_step)
        my_state.update(diag)
        my_state['time'] += model_time_step

Traj()

# pass_traj indicates completion of the script
with gzip.open(dir+'/pass_traj'+str(traj_num), 'wb') as f:
    pickle.dump([], f)
