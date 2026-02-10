import os
os.environ["NUMBA_NUM_THREADS"] = "4"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"

import xarray as xr
import zarr
import xcdat
import numpy as np
import pickle
import gzip
from sympl import get_constant
import time
import gc
import sys
import shutil
from concurrent.futures import ProcessPoolExecutor
import warnings
warnings.filterwarnings("ignore")


def interpolate_xcdat(climt_data):
    
    mid_levels = climt_data.mid_levels.values
    climt_data = climt_data.assign_coords({"mid_levels": mid_levels})

    climt_data['mid_levels'].attrs['axis'] = 'Z'
    climt_data['lat'].attrs['units'] = "degrees_north"


    # the axis name "lev" is not a choice, it's standard. Deviations will result in error
    pressure_grid = xcdat.create_grid(z = xcdat.create_axis("lev",
                                                           np.arange(100000,0,-2000)))
    pressure = climt_data['air_pressure']
    regridded_vars = []

    for var_name, var_data in climt_data.data_vars.items():
        #if var_name in ["eastward_wind", "northward_wind", "air_temperature", "vertical_wind"]:
            if 'mid_levels' in var_data.dims:
                output_var = climt_data.regridder.vertical(var_name,
                                                          pressure_grid,
                                                          method='linear',
                                                          target_data=pressure)[var_name]
                regridded_vars.append(output_var)

            else:
                output_var = climt_data[var_name]
                regridded_vars.append(output_var)

    merged_ds = xr.merge(regridded_vars)
    return merged_ds

def regrid(run):
    Rd = get_constant('gas_constant_of_dry_air', 'J kg^-1 K^-1')
    Cp =\
        get_constant('heat_capacity_of_dry_air_at_constant_pressure',
                     'J kg^-1 K^-1')
    g=get_constant('gravitational_acceleration',
                     'm s^-2') 

    common = xr.open_zarr("/scratch/steveleonpadua/aqua-planet/raw-data/common", consolidated=False)
    with gzip.open('/home/steveleonpadua/model-runs/dry-land/model_sigma', 'rb') as f:
            siga,sigb=pickle.load(f)
    #common=xr.open_zarr("/scratch/abel/steve/long-run-gw/common",consolidated=False)

    lat_rad=np.radians(common['latitude']).values[:]
    lon_rad=np.radians(common['longitude']).values[:]

    lat_deg=(common['latitude'])
    lon_deg=(common['longitude'])

    lat_diff=lat_deg[0,0]-lat_deg[1,0]
    lon_diff=lon_deg[0,1]-lon_deg[0,0]

    Lx=np.radians(lon_diff)*6371*1000
    Ly=np.radians(lat_diff)*6371*1000

    starttime = time.time()
  
    runs = [run]
    years = [f'year{i}' for i in range(1,21)]

    for run in runs:
        for year in years:
            diff_time = time.time()
            data=xcdat.open_dataset(f"/scratch/steveleonpadua/aqua-planet/raw-data/run{run}/{year}", consolidated=False, engine="zarr", add_bounds=None)
            

            data_out=[]
            i=0
            for e in data.time:
                i+=1    
                if i%100==0:
                    print('run',run, year, 'day',i , flush=True)
                #print(e)

                clim=data.sel({'time':e})

                # vertical wind calculation
                spress=clim['surface_air_pressure']
                uwind=clim['eastward_wind']
                nwind=clim['northward_wind']
                press=clim['air_pressure']


                eta=sigb.values[:,np.newaxis, np.newaxis]+(siga.values[:,np.newaxis, np.newaxis]-20)/(spress.values[:]-20)
                pint=siga.values[:,np.newaxis, np.newaxis]+sigb.values[:,np.newaxis, np.newaxis]*(spress.values[:]-20)

                dpdn=(pint[1:]-pint[:-1])/(eta[1:]-eta[:-1])
                udpdn=uwind.values[:]*dpdn
                vdpdn=nwind.values[:]*dpdn

                dudpdx=(udpdn[:,1:-1,2:]-udpdn[:,1:-1,:-2])/((lon_rad[1:-1,2:]-lon_rad[1:-1,:-2])*6371*1000*np.cos(lat_rad[1:-1,1:-1]))
                dvdpdy=(vdpdn[:,2:,1:-1]*np.cos(lat_rad[2:,1:-1])-vdpdn[:,:-2,1:-1]*np.cos(lat_rad[:-2,1:-1]))/((lat_rad[2:,1:-1]-lat_rad[:-2,1:-1])*6371*1000*np.cos(lat_rad[1:-1,1:-1]))

                dudpdx_full = np.full_like(uwind.values, np.nan)
                dvdpdy_full = np.full_like(nwind.values, np.nan)

                dudpdx_full[:,1:-1,1:-1] = dudpdx
                dvdpdy_full[:,1:-1,1:-1] = dvdpdy

                express=((dudpdx_full + dvdpdy_full)*(eta[:-1,:,:]-eta[1:,:,:]))[::-1]
                w=-np.cumsum(express, axis=0)

                dpdx=(press.values[:,1:-1,2:]-press.values[:,1:-1,:-2])/((lon_rad[1:-1,2:]-lon_rad[1:-1,:-2])*6371*1000*np.cos(lat_rad[1:-1,1:-1]))
                dpdy=(press.values[:,2:,1:-1]*np.cos(lat_rad[2:,1:-1])-press.values[:,:-2,1:-1]*np.cos(lat_rad[:-2,1:-1]))/((lat_rad[2:,1:-1]-lat_rad[:-2,1:-1])*6371*1000*np.cos(lat_rad[1:-1,1:-1]))

                dpdx_full = np.full_like(press.values, np.nan)
                dpdy_full = np.full_like(press.values, np.nan)

                dpdx_full[:,1:-1,1:-1] = dpdx
                dpdy_full[:,1:-1,1:-1] = dpdy

                w_res=(uwind.values * dpdx_full + nwind.values * dpdy_full)[::-1]

                w=(w+w_res)[::-1]

                omega_da = xr.DataArray(
                    data=w,
                    dims=['mid_levels', 'lat', 'lon'],
                    name='vertical_wind'
                )

                clim['vertical_wind'] = omega_da
                clim=clim.assign_coords({'lat':lat_deg.values[:,1], 'lon':lon_deg.values[1,:]})
                data_out.append(clim)

            data_out=xr.concat(data_out,dim='time')

            near_surface_zonal_wind = xr.DataArray(
                data=data_out['eastward_wind'][:,0,:,:],
                dims=['time', 'lat', 'lon'],
                name='near_surface_eastward_wind'
            )

            near_surface_meridional_wind = xr.DataArray(
                data=data_out['northward_wind'][:,0,:,:],
                dims=['time', 'lat', 'lon'],
                name='near_surface_northward_wind'
            )

            near_surface_air_temperature = xr.DataArray(
                data=data_out['air_temperature'][:,0,:,:],
                dims=['time', 'lat', 'lon'],
                name='near_surface_air_temperature'
            )
            data_out['near_surface_air_temperature']=near_surface_air_temperature
            data_out['near_surface_eastward_wind']=near_surface_zonal_wind
            data_out['near_surface_northward_wind']=near_surface_meridional_wind

            data_out= interpolate_xcdat(data_out)
            compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
            enc = {x: {"compressor": compressor} for x in data_out}
            #store = s3fs.S3Map(root=f"climt-long-runs/dry-land/regrid-data/run{run}/{year}", s3=mn, check=False)
            store = zarr.storage.DirectoryStore(f"/scratch/steveleonpadua/aqua-planet/regrid-data/run{run}/{year}")
            data_out.to_zarr(store=store, encoding=enc, mode='w')

            del data_out
            del data
            del clim
            gc.collect()

            print(run, year, "elapsed:",f"{(time.time() - starttime)/3600:.3f}", "hrs", flush=True)
            print("time_interval:", f"{(time.time() - diff_time)/3600:.3f}", flush=True)


start = int(sys.argv[1])
stop = int(sys.argv[2])

if __name__ == "__main__":
    runs = np.arange(start, stop)
    with ProcessPoolExecutor(max_workers=10) as executor:
        executor.map(regrid, runs)
