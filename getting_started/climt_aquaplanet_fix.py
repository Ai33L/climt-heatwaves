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


# function to save state to memory
def save_state(state, core, filename):

    spec = core._gfs_cython.get_spectral_arrays()

    with gzip.open(filename, 'wb') as f:
        pickle.dump([state,spec], f)


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
# dycore(my_state, model_time_step)

# Set initial/boundary conditions
latitudes = my_state['latitude'].values
longitudes = my_state['longitude'].values

surface_shape = latitudes.shape

# Set initial/boundary conditions
sw_max = 150
sw_min = 0

sw_flux_profile = (sw_max*(1+1.4*(1/4*(1-3*np.sin(np.radians(latitudes-10))**2))))
sw_flux_profile[np.where(latitudes<-80)]=sw_max*(1+1.4/4*(1-3))

my_state['downwelling_shortwave_flux_in_air'].values[:] = sw_flux_profile[np.newaxis, :]
my_state.update(optical_depth(my_state))
my_state['longwave_optical_depth_on_interface_levels'][0]=0

my_state['surface_temperature'].values[:] = 290.
my_state['ocean_mixed_layer_thickness'].values[:] = 2
my_state['soil_layer_thickness'].values[:] = 1

my_state['eastward_wind'].values[:] = np.random.randn(
    *my_state['eastward_wind'].shape)


# Run model for 3 years to spinup -- 
# First number should be multiple of 72 (1 day)
# 17 is subtracted for the timesteps to line up correctly for the daily average
for i in range(72*365*3-17):#26280 one year

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step

# save 3-year spinup
save_state(my_state, dycore, 'spinup_aquaplanet_3yr')

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

# Run model for 100 years and store data
for i in range(26280*100):#26280 one year
    
    if (i+1)%18==0:
        if data_flag==0:
            Data=format_data(my_state)
            data_flag=1
        else:
            Data=xr.combine_by_coords([Data,format_data(my_state)])

    # compress data by taking a daily average
    if (i+1)%2160==0:
        Data=Data.resample(time='1D').mean()
    
    if (i+1)%26280==0:
        data_flag=0
        compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
        enc = {x: {"compressor": compressor} for x in Data}

        store = zarr.storage.DirectoryStore("long_run/year"+str(index)) 
        (Data.resample(time='1D').mean()).to_zarr(store=store, encoding=enc, mode='w')
        index=index+1

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step
