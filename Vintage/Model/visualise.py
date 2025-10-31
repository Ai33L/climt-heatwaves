# Script to visualise model states and climatologies saved as gzip pickles

import warnings
warnings.filterwarnings("ignore")

from sympl import (PlotFunctionMonitor)
import numpy as np
from datetime import timedelta
import pickle
import time
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.transforms as mtransforms
import gzip


def set_label(fig, ax, label):
    trans = mtransforms.ScaledTranslation(5/72, -5/72, fig.dpi_scale_trans)
    ax.text(0.0, 1.0, label, transform=ax.transAxes + trans,
            fontsize='medium', verticalalignment='top', fontfamily='serif',
            bbox=dict(facecolor='1', edgecolor='none', pad=3.0, alpha=0.95))


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
    cs = ax.contourf(np.broadcast_to(state['latitude'][:,0].values[:], (28, 64)), state['air_pressure'].mean(dim='lon')/100,
    state['specific_humidity'].mean(dim='lon'), levels=16, cmap='Reds', robust=True)
    fig.colorbar(cs, ax=ax)
    ax.set_xlabel('Lat')
    ax.invert_yaxis()       
    ax.set_title('Specific humidity', fontsize=10)
    set_label(fig, ax,'f')

    fig.suptitle(my_state['time'], fontsize=12)

    fig.tight_layout()


import os
os.chdir(os.getcwd())

monitor = PlotFunctionMonitor(plot_function, interactive=False)

with gzip.open('spinup_3yr', 'rb') as f:
    
    my_state= pickle.load(f)[0]

    latitudes = np.radians(my_state['latitude'].values)
    longitudes = np.radians(my_state['longitude'].values)

    # plt.contourf(np.cos(latitudes))
    # plt.colorbar()
    # plt.show()

    print((my_state['air_temperature'][0]*np.cos(latitudes)).sum()/
    (np.cos(latitudes)).sum())
    
    mask = my_state['area_type'].astype('str') == 'land'

    print((my_state['air_temperature'][0]*(np.cos(latitudes)*mask)).sum()/
    (np.cos(latitudes)*mask).sum())

    print((my_state['surface_temperature']*(np.cos(latitudes)*mask)).sum()/
    (np.cos(latitudes)*mask).sum())

monitor.store(my_state)