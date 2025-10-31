import pickle
import time

var=0

import os
import sys

index=int(sys.argv[1])

time.sleep(30)
f = open("file"+str(index),'wb')
pickle.dump(var,f)
f.close()

