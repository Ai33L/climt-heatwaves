# script to create a mask for the observable
# here we create a 20x20 degrees square mask

import gzip
import pickle
import numpy as np
import matplotlib.pyplot as plt
import os

os.chdir(os.getcwd())

with gzip.open('spinup_3yr', 'rb') as f:
    state=pickle.load(f)[0]

lon=state['longitude']
lat=state['latitude']

obs_mask=np.zeros(lat.shape)

for i in range(128):
    for j in range(62):
        if (lat[j,i]>30 and lat[j,i]<50) and (lon[j,i]>100 and lon[j,i]<120): 
            obs_mask[j,i]=1

plt.contourf(lon, lat,obs_mask)
plt.show()

with gzip.open('obs_mask', 'wb') as f:
    pickle.dump(obs_mask ,f)