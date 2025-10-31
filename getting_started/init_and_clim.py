import warnings
warnings.filterwarnings("ignore")

import climt
from sympl import (TimeDifferencingWrapper)
import numpy as np
from datetime import timedelta
import pickle
import time
import gzip


# To save the state and spectral state of the model
# we use pickled format for convenience
def save_state(state, core, filename):

    spec = core._gfs_cython.get_spectral_arrays()

    with gzip.open(filename, 'wb') as f:
        pickle.dump([state,spec], f)


def init_and_clim(soil_conf=0.7, rad_conf=6):

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
    my_state['longwave_optical_depth_on_interface_levels'][0]=0

    my_state['surface_temperature'].values[:] = 290.
    my_state['ocean_mixed_layer_thickness'].values[:] = 2
    my_state['soil_layer_thickness'].values[:] = 1

    my_state['eastward_wind'].values[:] = np.random.randn(
        *my_state['eastward_wind'].shape)

    # setting the land
    for i in range(128):
        for j in range(64):
            l = my_state['latitude'][j,i]
            if (l>20 and l<60) or (l>-60 and l<-20):
                my_state['area_type'][j,i]=b'land'

    start_time = time.time()

    # spinup for 3 years
    for i in range(26280):#26280 one year
        diag, my_state = dycore(my_state, model_time_step)
        my_state.update(diag)
        my_state['time'] += model_time_step

    # save spinup if needed
    save_state(my_state, dycore, 'spinup_'+str(soil_conf)+'_'+str(rad_conf))

    # initialize dictionary for climatology
    state_clim = dict.fromkeys(my_state.keys(),0)

    count=0
    for i in range(26280):#26280 one year
        
        print(i)
        diag, my_state = dycore(my_state, model_time_step)
        my_state.update(diag)
        my_state['time'] += model_time_step

        if (i+1)%18==0:
            for e in state_clim.keys():
                if e!='time' and e!='area_type':
                    state_clim[e]+=my_state[e]
            count+=1
        
        ## save states at particular time intervals if needed
        #if (i+1)%720==0: # 720 is 10 days with 20min timestep
        #    n=int((i+1)/720)
        #    save_state(my_state, dycore, 'initial_'+str(soil_conf)+'_'+str(rad_conf)+'/state'+str(n))

    for e in state_clim.keys():
        if e!='time' and e!='area_type':
            state_clim[e].values[:]=state_clim[e]/count
    state_clim['area_type']=my_state['area_type']

    with gzip.open('climatology_'+str(soil_conf)+'_'+str(rad_conf), 'wb') as f:
            pickle.dump(state_clim, f)

    print("Time : ", (time.time() - start_time)/3600, "hrs")


init_and_clim(soil_conf=0.7, rad_conf=6)
