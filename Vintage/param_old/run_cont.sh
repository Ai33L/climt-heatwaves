#!/bin/bash

# remove old slurm files
rm -r *.sh.o*
rm -r *.sh.e*
rm GKTL_log.txt


# number of parallel trajectories
n=40


# loop over algorithm iterations
for (( k = 15; k <= 16 ; k++ ))
do

echo $k

c=1
x_prev=0
# submit inital set of jobs
for (( i = 1; i <= $n; i++ )) 
do 

pass=0
while [ $pass -ne 1 ]
do
if qsub submit_traj_ser.sh $1 $i $k > GKTL_log.txt; then
#echo $c
c=$((c+1))
pass=1
else
sleep 1
fi
done

done

# submit new jobs as old ones complete
while [ $c -le $3 ]
do
x=`find $1 -name 'traj_new*' |wc -l`

for (( i = 0; i < x-x_prev; i++ ))
do
if [ $c -le $3 ]
then

pass=0
while [ $pass -ne 1 ]
do
if qsub submit_traj_ser.sh $1 $c $k > GKTL_log.txt; then
#echo $c
c=$((c+1))
pass=1
else
sleep 1
fi
done

fi
done
x_prev=$x
sleep 120
done

# wait till al trajectory runs are completed
x=`find $1 -name 'traj_new*' |wc -l`
while [ $x -ne $3 ]
do
sleep 120
x=`find $1 -name 'traj_new*' |wc -l`
done

# run resampling for each iteration and check log
pass=0
while [ $pass -ne 1 ]
do
if qsub submit_resample.sh $1 $k > GKTL_log.txt; then
pass=1
else
sleep 1
fi
done
  
x=`find $1 -name 'resample_log*' |wc -l`
while [ $x -ne $k ]
do
sleep 120
x=`find $1 -name 'resample_log*' |wc -l`
done 

rm -r *.sh.o*
rm -r *.sh.e*

done

pass=0
while [ $pass -ne 1 ]
do
if qsub submit_wrap.sh $1 > GKTL_log.txt; then
pass=1
else
sleep 1
fi
done

x=`find $1 -name 'prob' |wc -l`
while [ $x -ne 1 ]
do
sleep 120
x=`find $1 -name 'prob' |wc -l`
done

rm -r *.sh.o*
rm -r *.sh.e*

echo 'done'
