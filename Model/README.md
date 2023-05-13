# Model

The baseline model was designed on CliMT. The fork of CliMT used can be found at <https://github.com/Ai33L/climt/tree/heatwave_sampling>

### Model description

Dynamical core

Parameterisations - 

* Gray radiation with Frierson longwave optical depths (default surface values, but linear with pressure)
* Slab surface - relative humidity scaling of 0.7 over land
* Moist convection (Emanuel scheme)
* Diffusive planetary boundary layer

Model resolution is T42 (64 x 128), with 28 vertical levels. The timestep of integration used is 20 minutes.

The incoming solar flux is set to be highest at 10$\degree$N, with the profile with latitude $\phi$ as $$150\LARGE(\normalsize 1+1.4\LARGE(\normalsize\frac{1-3sin\phi^2}{4}\LARGE)\LARGE) \normalsize W/m^2$$

In this model, we have implemented an idealised land configuration, with land extending from 20&deg; to 60&deg; in both hemispheres.

The depth of the land slab is set to 1 m, while the depth of the ocean slab is set to 2 m.

### Storing model data

The model data is stored using the Zarr storage format. The daily averaged model data is saved in the xarray dataset format.

Common data -

* longitude
* latitude
* area_type

These are saved before the model begins in the *common* directory.

Model data - 

* air_temperature
* air_pressure
* specific_humidity
* northward_wind
* eastward_wind 
* surface_air_pressure
* surface_temperature
* surface_upward_latent_heat_flux
* surface_upward_sensible_heat_flux
* boundary_layer_height
* divergence_of_wind
* surface_upwelling_longwave_flux_in_air
* surface_downwelling_longwave_flux_in_air

The daily averages of these are saved along the time axis in nested directories in xarray dataset format.

### Model analysis and others

1. The *model_state.pdf* file shows a model state after a 3 year spinup. From the area-averaged net flux at TOA, the model spinup time is around a year.

2. The *init_and_clim.py* script is used to perfom 3 year spinup and then compute the 30 year climatology of the model. The *visualise.py* script can then be used to plot and inspect the model state and climatology.

3. For heatwave analysis, we wish to focus on a region between 30&deg;N and 50&deg;N and 20&deg; wide. The *create_mask.py* script is used to make a mask that will be used later.

