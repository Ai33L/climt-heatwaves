import os
os.environ["NUMBA_NUM_THREADS"] = "7"
os.environ["OMP_NUM_THREADS"] = "7"
import xarray as xr
import pickle
import numpy as np
from sympl import get_constant
import metpy
from metpy.units import units
from concurrent.futures import ProcessPoolExecutor
import time
start_time = time.time()

output_dir='/home/steveleonpadua/model-runs/aqua-planet/'
base_path = "/scratch/steveleonpadua/aqua-planet/regrid-data/"

Rd = get_constant('gas_constant_of_dry_air', 'J kg^-1 K^-1')
Cp =\
    get_constant('heat_capacity_of_dry_air_at_constant_pressure',
                 'J kg^-1 K^-1')
g=get_constant('gravitational_acceleration',
                 'm s^-2') 

#dp=2000
#Lx=np.radians(2.8125)*6371*1000
#Ly=np.radians(2.79)*6371*1000

def compute_dse(ds, latc, lonc):
    # computes average DSE in the box between specified levels - units of J/kg
    
    p1=ds['air_pressure'].fillna(ds['surface_air_pressure'])
    at=ds['air_temperature'].fillna(ds['near_surface_air_temperature']).copy()
    at[:,1:]=(at.values[:,:-1]+at.values[:,1:])/2; at[:,0]=(at[:,0].values[:]+ds['near_surface_air_temperature'].values[:])/2
    p2=p1.copy()
    p2[:,1:]=p1[:,:-1].values[:]
    p2[:,0]=ds['surface_air_pressure'].values[:]
    
    lat_rad=np.radians(ds['air_temperature'].lat)
    
    z=(Rd*at/g*np.log(p2/p1)).cumsum(dim='lev')
    dse=(Cp*ds['air_temperature']+g*z).sel({'lat':slice(latc+5,latc-5),
                                            'lon':slice(lonc-5,lonc+5),'lev':slice(98000, 90000)}).weighted(np.cos(lat_rad))
    return dse.mean(dim=('lat', 'lon','lev'))

def compute_dse_tend(ds, latc, lonc):
    # computes average DSE tendency in the box between specified levels - units of J/kg
    
    p1=ds['air_pressure'].fillna(ds['surface_air_pressure'])
    at=ds['air_temperature'].fillna(ds['near_surface_air_temperature']).copy()
    at[:,1:]=(at.values[:,:-1]+at.values[:,1:])/2; at[:,0]=(at[:,0].values[:]+ds['near_surface_air_temperature'].values[:])/2
    p2=p1.copy()
    p2[:,1:]=p1[:,:-1].values[:]
    p2[:,0]=ds['surface_air_pressure'].values[:]
    
    lat_rad=np.radians(ds['air_temperature'].lat)
    
    z=(Rd*at/g*np.log(p2/p1)).cumsum(dim='lev')
    dse=Cp*ds['air_temperature']+g*z
    dsew=metpy.calc.first_derivative(dse, axis='lev')/units.metre
    dsex=metpy.calc.first_derivative(dse, axis='lon')
    dsey=metpy.calc.first_derivative(dse, axis='lat')
    dse_tend=-dsex*ds['eastward_wind']-dsey*ds['northward_wind']-dsew*ds['vertical_wind']
    dse_tend=(dse_tend).sel({'lat':slice(latc+5,latc-5),
                             'lon':slice(lonc-5,lonc+5),'lev':slice(98000, 90000)}).weighted(np.cos(lat_rad))
    
    return dse_tend.mean(dim=('lat', 'lon','lev'))*86400
    
def calculate_budget(latc):
    
    output_file=output_dir+'hw_'+str(latc)
    with open(output_file, 'rb') as f:
        hw_master=pickle.load(f)

    #target_lons = np.arange(5, 355, 60)
    target_lons = [105]
    mask = [lon in target_lons for lon in hw_master['lonc']]
    hw_master = {key: [vals[i] for i, m in enumerate(mask) if m]
                   for key, vals in hw_master.items()}

    hw_index=1

    y=1
    loop=0
    dse_master={'index':[], 'T':[], 'lonc':[], 'dse_low':[], 'dse_tend_low':[],
                  'intensity':[], 'duration':[], 'maximum':[]}

    full_length=len(hw_master['index'])

    while hw_index<=full_length:
        r=hw_master['run'][hw_index-1]
        zarr_path = base_path+"run"+str(r)+"/year"+str(y)
        ds = xr.open_zarr(zarr_path, consolidated=False)

        while(True):
            time_slice=hw_master['time'][hw_index-1]
            try:
                ds_hw=ds.sel({'time':time_slice})
                print(latc, hw_index, flush = True);loop=0

                dse_low=compute_dse(ds_hw, latc, hw_master['lonc'][hw_index-1])
                dse_tend_low=compute_dse_tend(ds_hw, latc, hw_master['lonc'][hw_index-1])
                dse_master['dse_low'].append(dse_low.values)
                dse_master['dse_tend_low'].append(dse_tend_low.values)
                for e in hw_master.keys():
                    if e in dse_master.keys():
                        dse_master[e].append(hw_master[e][hw_index-1])

                hw_index=hw_index+1
                if hw_index>full_length:
                    break
            except KeyError:
                loop=loop+1
                if loop>20:
                    print('skipping!', flush=True)
                    hw_index=hw_index+1
                    loop=0
                    break
                if y<20:
                    y=y+1
                else:
                    y=1
                break

    output_file=output_dir+'dse_mean_'+str(latc)
    if not os.path.isfile(output_file):
        with open(output_file, 'wb') as f:
            pickle.dump(dse_master, f)

            
if __name__ == "__main__":
    lats = [50, 35, 45]
    
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(calculate_budget, latc) for latc in lats]

        for future in futures:
            try:
                future.result() 
            except Exception as e:
                import traceback
                print("Subprocess failed with error:\n", traceback.format_exc())

                
print(f'time elapsed = {(time.time() - start_time)/3600:.4f}')                
#calculate_budget(50)
#calculate_budget(35)
#calculate_budget(45)
