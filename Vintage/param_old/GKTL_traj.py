import warnings
warnings.filterwarnings("ignore")

import climt
from sympl import (
    TimeDifferencingWrapper
)
import numpy as np
from datetime import timedelta
import pickle
import gzip


# get passed arguments
import sys
traj_num=int(sys.argv[1])
iter=int(sys.argv[2])
dir=str(sys.argv[3])
with open(dir+'/pert_flag', 'rb') as f:
    pert_flag = int(pickle.load(f)[traj_num-1])


# get tau value
with open(dir+'/config', 'rb') as f:
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
        
    with open(filename, 'rb') as f:
        fields, spec = pickle.load(f)
    if pert_flag:
        core.set_flag(False)
        perturb(spec)

    core._gfs_cython.reinit_spectral_arrays(spec)    
    state.update(fields)

# function to save state
def save_state(state, core, filename):
    
    spec = core._gfs_cython.get_spectral_arrays()

    with open(filename, 'wb') as f:
        pickle.dump([state,spec], f)


# trajectory simulation
def Traj():

    # Optional in our model - no component that uses irradiance
    climt.set_constants_from_dict({
        'stellar_irradiance': {'value': 200, 'units': 'W m^-2'}})

    model_time_step = timedelta(minutes=20)

    convection = climt.EmanuelConvection()
    boundary=TimeDifferencingWrapper(climt.SimpleBoundaryLayer(scaling_land=soil_conf))
    radiation = climt.GrayLongwaveRadiation()
    slab_surface = climt.SlabSurface()

    dycore = climt.GFSDynamicalCore(
        [boundary ,radiation, convection, slab_surface], number_of_damped_levels=5
    )

    grid = climt.get_grid(nx=128, ny=62)

    my_state = climt.get_default_state([dycore], grid_state=grid)
    dycore(my_state, model_time_step)

    load_state(my_state, dycore, dir+'/traj'+str(traj_num))

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
    
    # common save for latitude, longitude and area_type

    Longitude=my_state['longitude'].values[:]
    Latitude=my_state['latitude'].values[:]
    Area_type=my_state['area_type']

    with gzip.open(dir+'/common', 'wb') as f:
            pickle.dump([Longitude, Latitude, Area_type], f)

    with gzip.open('mask', 'rb') as f:
            obs_mask = pickle.load(f)

    def Obs(state):
        lat = np.radians(my_state['latitude'].values[:])
        O=state['air_temperature'][0].values[:]
        return((O*np.cos(lat)*obs_mask).sum())/((np.cos(lat)*obs_mask).sum())

    A=[] # to store observable

    for i in range(72*tau):#26280 one year

        if i==1:
            dycore.set_flag(True)

        diag, my_state = dycore(my_state, model_time_step)
        my_state.update(diag)
        my_state['time'] += model_time_step

        A.append(Obs(my_state))

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

        # write to file at end of trajectory simulation
        if (i+1)%(72*8)==0:
            
            with gzip.open(dir+'/A'+str(traj_num), 'wb') as f:
                pickle.dump(A, f)

            with gzip.open(dir+'/data_temp_'+str(iter)+'_'+str(traj_num), 'wb') as f:
                pickle.dump(Air_temp_lowest, f)

            with gzip.open(dir+'/data2D_'+str(iter)+'_'+str(traj_num), 'wb') as f:
                pickle.dump([Surf_temp, Surf_press, Down_long, Up_long, Latent_flux,
                Sensible_flux], f)
            
            with gzip.open(dir+'/data3D_'+str(iter)+'_'+str(traj_num), 'wb') as f:
                pickle.dump([Air_temp, East_wind, North_wind], f)

            save_state(my_state, dycore, dir+'/traj_new'+str(traj_num))

Traj()

# pass_traj indicates completion of the script
with open(dir+'/pass_traj'+str(traj_num), 'wb') as f:
    pickle.dump([], f)
