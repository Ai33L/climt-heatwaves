# Baseline model designed on CliMT

import warnings
warnings.filterwarnings("ignore")

import climt
from sympl import (TimeDifferencingWrapper, PlotFunctionMonitor)
import numpy as np
from datetime import timedelta
import time
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.transforms as mtransforms
import zarr 
import xarray as xr
import os

os.chdir(os.getcwd())

# Code to plot model state

def set_label(fig, ax, label):
    trans = mtransforms.ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans)
    ax.text(0.0, 1.0, label, transform=ax.transAxes + trans,
            fontsize='medium', verticalalignment='top', fontfamily='serif',
            bbox=dict(facecolor='1', edgecolor='none', pad=3.0, alpha=0.95))

F=[]

def plot_function(fig, state):
    
    fig.set_size_inches(11.3, 6.5)
    

    ax = fig.add_subplot(2, 3, 1)
    cs = ax.contourf(state['longitude'],state['latitude'],
    state['air_temperature'][0], levels=16, robust=True, cmap='Reds')
    fig.colorbar(cs, ax=ax)
    ax.set_xlabel('Lon')
    ax.set_ylabel('Lat')    
    ax.set_title('Air temperature(K)', fontsize=10)
    set_label(fig, ax,'a')

    up=np.max(state['surface_upward_sensible_heat_flux']).item() 
    down=np.abs(np.min(state['surface_upward_sensible_heat_flux']).item())
    lim=max(up,down)
    ax = fig.add_subplot(2, 3, 2)
    cs = ax.contourf(state['longitude'],state['latitude'],
    state['surface_upward_sensible_heat_flux'], levels=16, cmap='RdBu_r', robust=True, vmin=-lim, vmax=lim)
    fig.colorbar(cs, ax=ax)
    ax.set_xlabel('Lon')
    ax.set_title('Sensible flux(W m^-2)', fontsize=10)
    set_label(fig, ax,'b')
    
    up=np.max(state['surface_upward_latent_heat_flux']).item() 
    down=np.abs(np.min(state['surface_upward_latent_heat_flux']).item())
    lim=max(up,down)
    ax = fig.add_subplot(2, 3, 3)
    cs = ax.contourf(state['longitude'],state['latitude'],
    state['surface_upward_latent_heat_flux'], levels=16, cmap='RdBu_r', robust=True, vmin=-lim, vmax=lim)
    fig.colorbar(cs, ax=ax)
    ax.set_xlabel('Lon')
    ax.set_title('Latent flux(W m^-2)', fontsize=10)
    set_label(fig, ax,'c')
    
    ax = fig.add_subplot(2, 3, 4)
    cs = ax.contourf(np.broadcast_to(state['latitude'][:,0].values[:], (28, 64)), state['air_pressure'].mean(dim='lon')/100,
    state['air_temperature'].mean(dim='lon'), levels=16, cmap='Reds', robust=True)
    fig.colorbar(cs, ax=ax)
    ax.set_xlabel('Lat')
    ax.set_ylabel('Air pressure (hPa)')
    ax.invert_yaxis()       
    ax.set_title('Air temperature(K)', fontsize=10)
    set_label(fig, ax,'d')
    
    up=np.max(state['eastward_wind'].mean(dim='lon')).item() 
    down=np.abs(np.min(state['eastward_wind'].mean(dim='lon')).item())
    lim=max(up,down)
    ax = fig.add_subplot(2, 3, 5)
    cs = ax.contourf(np.broadcast_to(state['latitude'][:,0].values[:], (28, 64)), state['air_pressure'].mean(dim='lon')/100,
    state['eastward_wind'].mean(dim='lon'), levels=16, cmap='RdBu_r', robust=True, vmin=-lim, vmax=lim)
    fig.colorbar(cs, ax=ax)
    ax.set_xlabel('Lat')
    ax.invert_yaxis()       
    ax.set_title('Zonal Wind(m/s)', fontsize=10)
    set_label(fig, ax,'e')

    ax = fig.add_subplot(2, 3, 6)
    net_heat_flux = (
            state['downwelling_shortwave_flux_in_air'][-1] +
            state['downwelling_longwave_flux_in_air'][-1] -
            state['upwelling_shortwave_flux_in_air'][-1] -
            state['upwelling_longwave_flux_in_air'][-1])
    flux=(net_heat_flux*np.cos(np.radians(state['latitude'].values[:]))).mean()/(np.cos(np.radians(state['latitude'].values[:])).mean())
    ax.set_title('Net flux at TOA : '+ str(round(flux.item(),2))+' W/m^2', fontsize=10)
    F.append(flux.item())
    cs=ax.plot(np.array(range(len(F)))/(73/2),F)
    ax.set_xlabel('Time (year)')
    ax.set_ylabel('Flux')
    set_label(fig, ax,'f')

    fig.suptitle(my_state['time'], fontsize=12)

    fig.tight_layout()

    plt.savefig('model_state.pdf', bbox_inches='tight')


monitor = PlotFunctionMonitor(plot_function, interactive=True)

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


data_flag=0
# start_time = time.time()

# store common data before model start
arr_common=[]
for i in ['longitude','latitude','area_type']:
    arr_common.append(my_state[i].rename(i))
store = zarr.storage.DirectoryStore("data_baseline/common")
data_common=xr.merge(arr_common) 
data_common.to_zarr(store=store, mode='w')


# Spinup model for a year
for i in range(26280*3):#26280 one year

    if (i+1)%(72*10)==0:
        monitor.store(my_state)
    
    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step


# Run model for a day and store data
for i in range(72):#26280 one year

    if (i+1)%18==0:
        if data_flag==0:
            Data=format_data(my_state)
            data_flag=1
        else:
            Data=xr.combine_by_coords([Data,format_data(my_state)])

    diag, my_state = dycore(my_state, model_time_step)
    my_state.update(diag)
    my_state['time'] += model_time_step


# Saving model data to zarr

compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
enc = {x: {"compressor": compressor} for x in Data}

store = zarr.storage.DirectoryStore("data_baseline/day1") 
(Data.resample(time='1D').mean()).to_zarr(store=store, encoding=enc, mode='w')

# D=xr.open_zarr("data_baseline/day1")
# plt.contourf(D['surface_upward_sensible_heat_flux'][0])
# plt.colorbar()
# plt.show()