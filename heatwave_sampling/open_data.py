import zarr
import xarray as xr
import matplotlib.pyplot as plt

common=xr.open_zarr("climt_run/common",consolidated=False)
print(common)

data=xr.open_zarr("climt_run/run_data",consolidated=False)
print(data)

data['surface_air_pressure'].isel({'time':0}).plot()
plt.show()
