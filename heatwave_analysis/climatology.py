from minio import Minio
import s3fs
import os
import matplotlib.pyplot as plt
import xarray as xr
import pickle

fs = s3fs.S3FileSystem(
    client_kwargs={
        "endpoint_url": "http://192.168.1.237:9000"
    },
    key="d0d250b2541ac33f4660",
    secret="2fb32d964768bc94a3c0"
)

output_dir='/home/scratch/Abel_data/hw_processed/ctrl/'

ds_master=[]
for r in range(1,51):
    print(r)
    ds_temp=[]
    for y in range(1,21):

        # Path inside the bucket to your Zarr store
        zarr_path = "abel-long-run/Regridded_data/run"+str(r)+"/year"+str(y)
        ds = xr.open_zarr(fs.get_mapper(zarr_path))
        ds_temp.append(ds.mean(dim='time'))
        
    ds_master.append(xr.concat(ds_temp, dim="ensemble").mean(dim="ensemble"))
    ds_temp=[]
    
ds_mean=xr.concat(ds_master, dim="ensemble").mean(dim="ensemble")
outfile=output_dir+'climatology.nc'
ds_mean.to_netcdf(outfile)