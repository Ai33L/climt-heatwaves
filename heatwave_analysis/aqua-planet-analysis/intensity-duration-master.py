import os
os.environ["NUMBA_NUM_THREADS"] = "5"
os.environ["OMP_NUM_THREADS"] = "5"
import time
import sys
import xarray as xr
import pickle
import numpy as np
from sympl import get_constant
import metpy
from metpy.units import units
from concurrent.futures import ProcessPoolExecutor

start_time = time.time()
output_dir='/home/steveleonpadua/model-runs/aqua-planet/'
base_path = "/scratch/steveleonpadua/aqua-planet/regrid-data/"


Rd = get_constant('gas_constant_of_dry_air', 'J kg^-1 K^-1')
Cp =\
    get_constant('heat_capacity_of_dry_air_at_constant_pressure',
                 'J kg^-1 K^-1')
g=get_constant('gravitational_acceleration',
                 'm s^-2') 

climfile=output_dir+'climatology'
ds=xr.open_dataset(climfile, engine='zarr')

p1=ds['air_pressure'].fillna(ds['surface_air_pressure'])
at=ds['air_temperature'].fillna(ds['near_surface_air_temperature']).copy()
at[1:, :]=(at.values[:-1, :]+at.values[1:, :])/2; at[0, :]=(at[0, :].values[:]+ds['near_surface_air_temperature'].values[:])/2
p2=p1.copy()
p2[1:,:]=p1[:-1,:].values[:]
p2[0,:]=ds['surface_air_pressure'].values[:]

lat_rad=np.radians(ds['air_temperature'].lat)

z=(Rd*at/g*np.log(p2/p1)).cumsum(dim='lev')

dse_clim=Cp*ds['air_temperature']+g*z
u_clim=ds['eastward_wind']; v_clim=ds['northward_wind']; w_clim=ds['vertical_wind']

def avg_cons(x):
    return (x.values[1:]+x.values[:-1])/2

def diff_cons(x):
    return (x.values[1:]-x.values[:-1])


# change the .mean to .sum at the end of compute_dse and compute_dse_tend, 
# if youre selecting levs from 960 and upwards, 980 has nans which will
# interfere with the sum values (960 and upwards is devoid of nans), taking
# mean will help smooth it out. 

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
    # computes average DSE tendency Reynolds components in the box between specified levels - units of J/kg

    p1=ds['air_pressure'].fillna(ds['surface_air_pressure'])
    at=ds['air_temperature'].fillna(ds['near_surface_air_temperature']).copy()
    at[:,1:]=(at.values[:,:-1]+at.values[:,1:])/2; at[:,0]=(at[:,0].values[:]+ds['near_surface_air_temperature'].values[:])/2
    p2=p1.copy()
    p2[:,1:]=p1[:,:-1].values[:]
    p2[:,0]=ds['surface_air_pressure'].values[:]

    lat_rad=np.radians(ds['air_temperature'].lat)

    z=(Rd*at/g*np.log(p2/p1)).cumsum(dim='lev')
    dse=Cp*ds['air_temperature']+g*z

    # adding the dse components to a list
    rey_grp=[]
    rey_grp.append(-metpy.calc.first_derivative(dse, axis='lev')/units.metre*ds['vertical_wind'])
    rey_grp.append(-metpy.calc.first_derivative(dse-dse_clim, axis='lat')*(ds['northward_wind']-v_clim))
    rey_grp.append(-metpy.calc.first_derivative(dse_clim, axis='lat')*(ds['northward_wind']-v_clim))
    rey_grp.append(-metpy.calc.first_derivative(dse-dse_clim, axis='lat')*(v_clim))
    rey_grp.append(-metpy.calc.first_derivative(dse_clim, axis='lat')*(v_clim))
    rey_grp.append(-metpy.calc.first_derivative(dse-dse_clim, axis='lon')*(ds['eastward_wind']-u_clim))
    rey_grp.append(-metpy.calc.first_derivative(dse_clim, axis='lon')*(ds['eastward_wind']-u_clim))
    rey_grp.append(-metpy.calc.first_derivative(dse-dse_clim, axis='lon')*(u_clim))
    rey_grp.append(-metpy.calc.first_derivative(dse_clim, axis='lon')*(u_clim))
    rey_grp.append(-metpy.calc.first_derivative(dse, axis='lon')*ds['eastward_wind']
                   -metpy.calc.first_derivative(dse, axis='lat')*ds['northward_wind']
                   -metpy.calc.first_derivative(dse, axis='lev')/units.metre*ds['vertical_wind'])


    rey_out=[]
    for e in rey_grp:
        rey_out.append((e).sel({'lat':slice(latc+5,latc-5), 'lon':slice(lonc-5,lonc+5),
                                'lev':slice(98000, 90000)}).weighted(np.cos(lat_rad)).mean(dim=('lat', 'lon','lev'))*86400)

    return rey_out


#ID = intensity or duration
#LH = low or high

def master_fn(ID, LH, latc):
    print(latc, ID, LH, flush=True)
    if ID=='I':
        metric = 'intensity'
    elif ID=='D':
        metric = 'duration'
    
    if LH=='L':
        quant = 0.1
        sign = '<'
    elif LH=='H':
        quant= 0.9
        sign = '>'

    def get_comparator(sign):
        if sign == ">":
            return lambda a, b: a > b
        elif sign == "<":
            return lambda a, b: a < b
        
    compare_op = get_comparator(sign)   

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
    dse_master={'index':[], 'T':[], 'lonc':[], 'dse_low':[], 'intensity':[], 'duration':[], 'maximum':[],
                'dseres':[],'dsez':[],'dsexaa':[],'dsexca':[],'dsexac':[],'dsexcc':[],'dseyaa':[],'dseyca':[],
                'dseyac':[],'dseycc':[], 'dsetot':[]}

    full_length=len(hw_master['index'])
    qval = np.quantile(hw_master[metric], quant)
    
    while hw_index <= full_length:
        try:
            if compare_op(hw_master[metric][hw_index-1], qval):
                r = hw_master['run'][hw_index-1]
                zarr_path = f"{base_path}run{r}/year{y}/"
                ds = xr.open_zarr(zarr_path, consolidated=False)

                time_slice = hw_master['time'][hw_index-1]
                ds_hw = ds.sel({'time': time_slice})
                print(ID,LH, latc, hw_index , hw_master['index'][hw_index-1],flush=True); loop = 0

                dse_low = compute_dse(ds_hw, latc, hw_master['lonc'][hw_index-1])
                dse_tend_low = compute_dse_tend(ds_hw, latc, hw_master['lonc'][hw_index-1])
                dse_master['dse_low'].append(dse_low.values)

                dse_master['dsez'].append(avg_cons(dse_tend_low[0]))
                dse_master['dseyaa'].append(avg_cons(dse_tend_low[1]))
                dse_master['dseyca'].append(avg_cons(dse_tend_low[2]))
                dse_master['dseyac'].append(avg_cons(dse_tend_low[3]))
                dse_master['dseycc'].append(np.array(dse_tend_low[4].values))
                dse_master['dsexaa'].append(avg_cons(dse_tend_low[5]))
                dse_master['dsexca'].append(avg_cons(dse_tend_low[6]))
                dse_master['dsexac'].append(avg_cons(dse_tend_low[7]))
                dse_master['dsexcc'].append(np.array(dse_tend_low[8].values))
                dse_master['dsetot'].append(avg_cons(dse_tend_low[9]))
                dse_master['dseres'].append(diff_cons(dse_low)-avg_cons(dse_tend_low[9]))

                for e in hw_master.keys():
                    if e in dse_master.keys():
                        dse_master[e].append(hw_master[e][hw_index-1])
            hw_index += 1  # always advance
        except KeyError:
            loop += 1
            if loop > 20:
                print("skipping!")
                hw_index += 1
                loop = 0
                continue
            if y < 20:
                y += 1
            else:
                y = 1


                
    output_file=output_dir+'dse_rey_'+LH+ID+'_'+str(latc)
    if not os.path.isfile(output_file):
        with open(output_file, 'wb') as f:
            pickle.dump(dse_master, f)
            
if __name__ == "__main__":
    params = [('I','H',35),('I','H',50),('D','H',35),('D','H',50),('D','L',35),('D','L',50),('I','L',35),('I','L',50)]
    
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(master_fn, a, b, c) for (a,b,c) in params]

        for future in futures:
            try:
                future.result() 
            except Exception as e:
                import traceback
                print("Subprocess failed with error:\n", traceback.format_exc())

print(f'time elapsed = {(time.time() - start_time)/3600:.4f}')  
