# runs the model for short durations (50 years) - run many times for a total duration of
# 1000 years

import warnings
warnings.filterwarnings("ignore")
# import os
# os.environ['OPENMP_NUM_THREADS']='2'

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
import gzip

import sys
key=int(sys.argv[1])

# Function to perturb spectral surface pressure array - To introduce perturbation in model
def perturb(X):
    X=np.array(X)
    N=np.random.uniform(-1,1,np.shape(X[4]))*np.sqrt(2)*10**-4
    X[4][:]=(X[4]+N)[:]

#load state from memory
def load_state(state, core, filename):
        
    with open(filename, 'rb') as f:
        fields, spec = pickle.load(f)
        
    if pert_flag:
        core.set_flag(False)
        perturb(spec)

    core._gfs_cython.reinit_spectral_arrays(spec)    
    state.update(fields)

pert_flag=1

# Optional in our model - no component that uses irradiance
climt.set_constants_from_dict({
    'stellar_irradiance': {'value': 200, 'units': 'W m^-2'}})

model_time_step = timedelta(minutes=20)

# Create components
convection = climt.EmanuelConvection()
boundary=TimeDifferencingWrapper(climt.SimpleBoundaryLayer(scaling_land=0.5))
radiation = climt.GrayLongwaveRadiation()
slab_surface = climt.SlabSurface()
optical_depth = climt.Frierson06LongwaveOpticalDepth(linear_optical_depth_parameter=1, longwave_optical_depth_at_equator=6)

dycore = climt.GFSDynamicalCore(
    [boundary ,radiation, convection, slab_surface], number_of_damped_levels=5
)

grid = climt.get_grid(nx=128, ny=62)

# Create model state
my_state = climt.get_default_state([dycore], grid_state=grid)
dycore(my_state, model_time_step)

load_state(my_state, dycore, 'initial_summer_0.5_6/state1000')

# spinup from perturbed state - to be safe from effects of perturbation
for i in range(26280):#26280 one year

    if i==1:
        dycore.set_flag(True)

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step

# setup fields to save
# Temp field
Air_temp_lowest=[]
# 2D fields
Surf_temp=[]
Surf_press=[]
Down_long=[]
Up_long=[]
Latent_flux=[]
Sensible_flux=[]
# 3D fields
Air_temp=[]
East_wind=[]
North_wind=[]

file_no = (key-1)*5+1

# common save for latitude, longitude and area_type

Longitude=my_state['longitude'].values[:]
Latitude=my_state['latitude'].values[:]
Area_type=my_state['area_type']

with gzip.open('long_run2/common', 'wb') as f:
        pickle.dump([Longitude, Latitude, Area_type], f)

for i in range(26280*25):#26280 one year

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step

    #saving temp field
    if (i+1)%3==0:
        Air_temp_lowest.append(np.around(my_state['air_temperature'].values[0], 2))

    #saving 2D fields
    if (i+1)%18==0:
        Surf_temp.append(np.around(my_state['surface_temperature'].values[0],2))
        Surf_press.append(np.around(my_state['surface_air_pressure'].values[0],2))
        Down_long.append(np.around(my_state['downwelling_longwave_flux_in_air'].values[0],2))
        Up_long.append(np.around(my_state['upwelling_longwave_flux_in_air'].values[0],2))
        Latent_flux.append(np.around(my_state['surface_upward_latent_heat_flux'].values[:],2))
        Sensible_flux.append(np.around(my_state['surface_upward_sensible_heat_flux'].values[:],2))

    #saving 3D fields
    if (i+1)%72==0:
        Air_temp.append(np.around(my_state['air_temperature'].values[:20], 2))
        East_wind.append(np.around(my_state['eastward_wind'].values[:20],3))
        North_wind.append(np.around(my_state['northward_wind'].values[:20],3))

    if (i+1)%(26280*5)==0:

        with gzip.open('long_run2/data_temp_'+str(file_no), 'wb') as f:
            pickle.dump(Air_temp_lowest, f)

        with gzip.open('long_run2/data2D_'+str(file_no), 'wb') as f:
            pickle.dump([Surf_temp, Surf_press, Down_long, Up_long, Latent_flux,
            Sensible_flux], f)
        
        with gzip.open('long_run2/data3D_'+str(file_no), 'wb') as f:
            pickle.dump([Air_temp, East_wind, North_wind], f)

        file_no=file_no+1
        
        Air_temp_lowest=[]

        Surf_temp=[]
        Surf_press=[]
        Down_long=[]
        Up_long=[]
        Latent_flux=[]
        Sensible_flux=[]

        Air_temp=[]
        East_wind=[]
        North_wind=[]
