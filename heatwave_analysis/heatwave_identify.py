import s3fs
import xarray as xr
import numpy as np
import pickle
import os
from concurrent.futures import ProcessPoolExecutor

output_dir = "/home/data/lab_project2/Steve/model_runs/aqua_planet/1/"
base_path = "abel-long-run/aqua-planet/regridded-data/"

output_file=output_dir+'thresh95'
with open(output_file, 'rb') as f:
    thresh=pickle.load(f)
# print(thresh)

def identify_heatwaves(latc):
    
        
    fs = s3fs.S3FileSystem(
        client_kwargs={
            "endpoint_url": "http://192.168.1.237:9000"
        },
        key="d0d250b2541ac33f4660",
        secret="2fb32d964768bc94a3c0"
    )
    
    hw_index=1
    hw_master={'index':[],'run':[],'time':[], 'T':[], 'lonc':[],
              'intensity':[], 'duration':[], 'maximum':[]}
    lon_ind=np.arange(36)*10+5
    
    #for ln in lon_ind[:]:        
    for r in range(1,6):
        t_run_all=[]
        for y in range(1,21):

            # Path inside the bucket to your Zarr store
            zarr_path = base_path+"run"+str(r)+"/year"+str(y)
            ds = xr.open_zarr(fs.get_mapper(zarr_path))
            t_run_all.append(ds['air_temperature'].sel({'lev': 98000, 'lat':slice(latc+5, latc-5)}))

        t_run_all=xr.concat(t_run_all, dim='time')
        t_run_all = t_run_all.weighted(t_run_all.lat).mean(dim='lat') - thresh[latc]
        
        for ln in lon_ind[:]:
            t_run = t_run_all.sel({'lon':slice(ln-5,ln+5)}).mean(dim='lon')
            # for loop to find heatwaves - there may be a better way to do this!
            
            T = t_run.values
            times = t_run.time.values
            
            temp_time=[]
            temp_intensity=[]
            l_curr=0
            for i in range(len(T)):
                if T[i]>0 and i!=0:
                    if len(temp_time)==0:
                        temp_time.append(times[i-1]); temp_intensity.append(T[i-1]) 
                    temp_time.append(times[i]); temp_intensity.append(T[i]) 
                    l_curr=l_curr+1
                else:
                    if l_curr>=3:
                        temp_time.append(times[i]); temp_intensity.append(T[i]) 
                        
                        heat=np.array(temp_intensity, dtype=float)

                        st=1-heat[0]/(heat[0]-heat[1]); end=heat[-2]/(heat[-2]-heat[-1])
                        heat[0]=0;heat[-1]=0
                        dur_weight=np.ones(len(heat)-1); dur_weight[0]=st;dur_weight[-1]=end
                        intensity=np.average((heat[1:]+heat[:-1])/2,weights=dur_weight)
                        mx=np.max(heat[1:-1])
                        dur=len(heat[1:-1])-1+st+end

                        if dur>=3:
                            print(f'lat{latc} run{r} lonc{ln} index{hw_index}')
                            hw_master['index'].append(hw_index)
                            hw_master['run'].append(r)
                            hw_master['time'].append(temp_time)
                            hw_master['T'].append(temp_intensity)
                            hw_master['intensity'].append(intensity.item())
                            hw_master['duration'].append(dur.item())
                            hw_master['maximum'].append(mx.item())
                            hw_master['lonc'].append(ln.item())
                            hw_index=hw_index+1

                    l_curr=0
                    temp_intensity=[]
                    temp_time=[]
                    
    print(hw_master['index'][-1])
    output_file=output_dir+'hw_'+str(latc)
    if not os.path.isfile(output_file):
        with open(output_file, 'wb') as f:
            pickle.dump(hw_master, f)

if __name__ == "__main__":
    lats = [35,40, 45,50]
    with ProcessPoolExecutor(max_workers=28) as executor:
        futures = [executor.submit(identify_heatwaves, lat) for lat in lats]

        for future in futures:
            try:
                future.result() 
            except Exception as e:
                import traceback
                print("Subprocess failed with error:\n", traceback.format_exc())

