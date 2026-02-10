import warnings
warnings.filterwarnings("ignore")
import os
os.environ["NUMBA_NUM_THREADS"] = "4"
os.environ["OMP_NUM_THREADS"] = "4"

import climt
from sympl import (TimeDifferencingWrapper)
import numpy as np
from datetime import timedelta
import pickle
import time
import gzip
import xarray as xr
from concurrent.futures import ProcessPoolExecutor
import sys
import zarr


# sets perturbation of loaded state
pert_flag=1

# Function to perturb spectral surface pressure array
# seeds based on the run number. 
def perturb(X, seed=None):
    if seed is not None:
        np.random.seed(seed)
    X=np.array(X)
    N=np.random.uniform(-1,1,np.shape(X[4]))*np.sqrt(2)*10**-4
    X[4][:]=(X[4]+N)[:]

# function to load state from memory
def load_state(state, core, filename, run):
        
    with gzip.open(filename, 'rb') as f:
        fields, spec = pickle.load(f)
        
    if pert_flag:
        core.set_flag(False)
        perturb(spec, seed=run)

    core._gfs_cython.reinit_spectral_arrays(spec)    
    state.update(fields)


def long_run(run):
    #run=1

    
    print(f"[start] run {run} pid={os.getpid()}", flush=True)
    soil_conf=0.7
    rad_conf=6

    model_time_step = timedelta(minutes=20)

    convection = climt.EmanuelConvection()
    boundary=TimeDifferencingWrapper(climt.SimpleBoundaryLayer(scaling_land=soil_conf))
    radiation = climt.GrayLongwaveRadiation()
    slab_surface = climt.SlabSurface()
    optical_depth = climt.Frierson06LongwaveOpticalDepth(linear_optical_depth_parameter=1, longwave_optical_depth_at_equator=rad_conf)

    dycore = climt.GFSDynamicalCore(
        [boundary ,radiation, convection, slab_surface], number_of_damped_levels=5
    )

    grid = climt.get_grid(nx=128, ny=64)
    my_state = climt.get_default_state([dycore], grid_state=grid)
    dycore(my_state, model_time_step)

    load_state(my_state, dycore,'/scratch/steveleonpadua/aqua-planet/spinup_0.7_6', run)

    start_time = time.time()

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
                if i in ['air_temperature']:
                    arr.append(state[i][0].rename('surface_'+i).astype('float32'))

        data=xr.merge(arr)

        # sets lat-lon coordinates
        lats=state['latitude'].values[:,0]; lons=state['longitude'].values[0,:]
        data=data.assign_coords({"lat": lats, 'lon': lons})

        data = data.expand_dims(time=[my_state['time']])

        return(data)

    if run==1:
        # store common data before model start
        arr_common=[]
        for i in ['longitude','latitude','area_type']:
            arr_common.append(my_state[i].rename(i))
        #store = s3fs.S3Map(root=f"climt-long-runs/dry-land/raw-data/common", s3=mn, check=False) 
        store = zarr.storage.DirectoryStore(f"/scratch/steveleonpadua/aqua-planet/raw-data/common")
        data_common=xr.merge(arr_common) 
        data_common.to_zarr(store=store, mode='w')


    data_flag=0
    day_index=0
    year_index = 1
    day_flag=0
    compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
    enc = None

    for i in range(26280*20):

        if (i+1)%18==0: # recording data for every 6 hours
            if data_flag== 0:
                Data = format_data(my_state)
                data_flag=1
            else:
                Data=xr.combine_by_coords([Data, format_data(my_state)])

        if (i+1)%72==0:
            #print('day', day_index)
            day_index+=1
            data_flag=0
            Data = Data.resample(time='1D').mean()
            #compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
            if enc is None:
                enc = {x: {"compressor": compressor} for x in Data}
             

            store = zarr.storage.DirectoryStore(f"/scratch/steveleonpadua/aqua-planet/raw-data/run{run}/year{year_index}")
            if day_flag==0:
                day_flag=1
                Data.to_zarr(store=store, encoding=enc, mode='w')

            else:
                Data.to_zarr(store=store, mode="a",append_dim="time")

            print(f'run{run} year{year_index} day{day_index}  time elapsed = {(time.time() - start_time)/3600:.4f} hrs', flush=True)   

        if (i+1)%26280==0:
            year_index+=1
            day_index = 0
            day_flag = 0

        diag, my_state = dycore(my_state, model_time_step)
        my_state.update(diag)
        my_state['time'] += model_time_step


start = int(sys.argv[1])
stop = int(sys.argv[2])

if __name__ == "__main__":
    runs = np.arange(start, stop)
    with ProcessPoolExecutor(max_workers=40) as executor: 
        executor.map(long_run, runs)

