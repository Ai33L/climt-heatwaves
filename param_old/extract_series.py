import pickle
import gzip
import numpy as np


with gzip.open('long_run/common', 'rb') as f:
    lat=np.radians(pickle.load(f)[1])

with gzip.open('mask', 'rb') as f:
    mask=pickle.load(f)

ser=[]
for i in range(200):
    with gzip.open('long_run/data_temp_'+str(i+1), 'rb') as f:
        dat=pickle.load(f)

    for e in dat:
        obs=((e*np.cos(lat)*mask).sum())/((np.cos(lat)*mask).sum())
        ser.append(obs)

with gzip.open('long_series', 'wb') as f:
    pickle.dump(ser, f)
