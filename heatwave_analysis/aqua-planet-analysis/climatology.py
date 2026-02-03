import zarr
import xarray as xr
import gzip
import pickle
import numpy as np
import time


output_dir = "/home/steveleonpadua/model-runs/aqua-planet/"
base_path = "/scratch/steveleonpadua/aqua-planet/regrid-data/"

start_time = time.time()
ds_master=[]
for r in range(1,51):
    ds_temp=[]
    for y in range(1,21):
        print(r, y)

        # Path inside the bucket to your Zarr store
        zarr_path = base_path+"run"+str(r)+"/year"+str(y)
        ds = xr.open_zarr(zarr_path, consolidated = False)
        ds_compute = ds.mean(dim='time').compute()
        ds_temp.append(ds_compute)
           
    ds_master.append(xr.concat(ds_temp, dim="ensemble").mean(dim="ensemble"))
    ds_temp=[]
    
ds_mean=xr.concat(ds_master, dim="ensemble").mean(dim="ensemble")
compressor = zarr.Blosc(cname="lz4hc", clevel=5, shuffle=True)
enc = {x: {"compressor": compressor} for x in ds_mean}
store = zarr.storage.DirectoryStore(output_dir+"climatology") 
(ds_mean).to_zarr(store=store, encoding=enc, mode='w')

print(f'time elapsed = {(time.time() - start_time)/3600:.4f} hrs')  


