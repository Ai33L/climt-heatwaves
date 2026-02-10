print('start')
import warnings
warnings.filterwarnings("ignore")

import os
os.environ["NUMBA_NUM_THREADS"] = "10"
os.environ["OMP_NUM_THREADS"] = "10"
os.environ["MKL_NUM_THREADS"] = "10"
os.environ["OPENBLAS_NUM_THREADS"] = "10"
os.environ["VECLIB_MAXIMUM_THREADS"] = "10"
os.environ["NUMEXPR_NUM_THREADS"] = "10"

import climt
from sympl import (TimeDifferencingWrapper)
import numpy as np
from datetime import timedelta
import pickle
import time
import gzip
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

base_path = '/scratch/steveleonpadua/aqua-planet/'

# To save the state and spectral state of the model
# we use pickled format for convenience
def save_state(state, core, filename):

    spec = core._gfs_cython.get_spectral_arrays()

    with gzip.open(filename, 'wb') as f:
        pickle.dump([state,spec], f)


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

# Create model state
my_state = climt.get_default_state([dycore], grid_state=grid)

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
# my_state['longwave_optical_depth_on_interface_levels'][0]=0

my_state['surface_temperature'].values[:] = 290.
my_state['ocean_mixed_layer_thickness'].values[:] = 2
my_state['soil_layer_thickness'].values[:] = 1

my_state['eastward_wind'].values[:] = np.random.randn(
    *my_state['eastward_wind'].shape)

start_time = time.time()

net_flux_list = []
time_list = []
weights = np.cos(np.deg2rad(my_state['latitude']))

# spinup for 3 years
for i in range(26280*3):#26280 one year
    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step

    if (i+1) % 72 ==0: #this is for a day

        #net-flux calculation
        lw_up = my_state['upwelling_longwave_flux_in_air'][28]
        sw_down = my_state['downwelling_shortwave_flux_in_air'][28]
        time_val = my_state['time']

        net_flux = np.average((sw_down - lw_up),weights=weights)

        net_flux_list.append(net_flux)
        time_list.append(time_val)

        #save_state(my_state, dycore, f'spinup_day_{(i+1)/72}')
        print(f'day{(i+1)/72}  time elapsed = {(time.time() - start_time)/3600:.4f} hrs')
        
#plotting
plt.plot(time_list, net_flux_list)
plt.gca().xaxis.set_major_locator(mdates
                                    .YearLocator())
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
#plt.ylim(-50000, 10000)
plt.xlabel('Year')
plt.ylabel('W/m²')
plt.title(f'Net flux at TOA: {net_flux_list[-1]:.1f} W/m²' )
plt.savefig(f'{base_path}net_flux_spinup_{soil_conf}_{rad_conf}.jpg', dpi=300, bbox_inches='tight')
#plt.show()



# save spinup if needed
save_state(my_state, dycore, base_path + 'spinup_'+str(soil_conf)+'_'+str(rad_conf))

print("Time : ", (time.time() - start_time)/3600, "hrs")
print("Spin-up done")

