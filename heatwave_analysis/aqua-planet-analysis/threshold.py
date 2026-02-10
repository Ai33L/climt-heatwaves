print('start')
import s3fs
import xarray as xr
import numpy as np
import pickle
import os
import gzip

fs = s3fs.S3FileSystem(
    client_kwargs={
        "endpoint_url": "http://192.168.1.237:9000"
    },
    key="d0d250b2541ac33f4660",
    secret="2fb32d964768bc94a3c0"
)

output_dir = "/home/steveleonpadua/model-runs/aqua-planet/"
base_path = "/scratch/steveleonpadua/aqua-planet/regrid-data/"

def compute_threshold():
    
    lat_c=[35,40,45,50]
    thresh={}
    
    for l in lat_c:
        print(l)
        
        t_all=[]
        for r in range(1,51):
            t_run=[]
            for y in range(1,21):

                # Path inside the bucket to your Zarr store
                zarr_path = base_path+"run"+str(r)+"/year"+str(y)
                ds = xr.open_zarr(zarr_path, consolidated = False)

                t_run.append(ds['air_temperature'].sel({'lev': 98000, 'lat':slice(l+5, l-5), 'lon':slice(100, 110)}))
        
            t_run=xr.merge(t_run, compat='no_conflicts', join='outer')
            t_run=t_run.weighted(t_run.lat).mean(dim=('lat', 'lon'))
            t_all.append(t_run)

        thresh[l]=xr.concat(t_all, dim="run")['air_temperature'].quantile(0.95, dim=('run', 'time')).compute().item()
    
    print(thresh)
    output_file=output_dir+'thresh95'
    if not os.path.isfile(output_file):
        with open(output_file, 'wb') as f:
            pickle.dump(thresh, f)

        
compute_threshold()
