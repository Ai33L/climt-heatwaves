#!/bin/bash

# Function to run an experiment
# Arguments-
# 1 - Directory to run experiment in
# 2 - Value of selection coefficient to be used
# 3 - Number of trajectories to be run
# 4 - Directory of initial states 
run_exp(){

# clear slurm logs
rm -r *.sh.o*
rm -r *.sh.e*
rm GKTL_log.txt

echo "starting new experiment"
# create directory for experiment
rm -r $1
mkdir $1

# run GKTL_init
qsub submit_init.sh $1 $2 $3 $4 > GKTL_log.txt

# proceed only if pass_init file is found in direcotry
x=`find $1 -name 'pass_init' |wc -l`
while [ $x -ne 1 ]
do
sleep 60
x=`find $1 -name 'pass_init' |wc -l`
done

# end of initialisation - iteration begin

n=40 # number of parallel trajectories

# loop over algorithm iterations
for (( k = 1; k <= 16 ; k++ ))
do

echo $k

# submit jobs - n jobs at a time
c=1
x_prev=0
for (( i = 1; i <= $n; i++ )) 
do 

qsub submit_traj_ser.sh $1 $i $k > GKTL_log.txt
#echo $c
c=$((c+1))

done

while [ $c -le $3 ]
do
x=`find $1 -name 'pass_traj*' |wc -l`

for (( i = 0; i < x-x_prev; i++ ))
do
if [ $c -le $3 ]
then

qsub submit_traj_ser.sh $1 $c $k > GKTL_log.txt
#echo $c
c=$((c+1))

fi
done

x_prev=$x
sleep 120

done

# wait till all trajectory runs are completed
x=`find $1 -name 'pass_traj*' |wc -l`
while [ $x -ne $3 ]
do
sleep 120
x=`find $1 -name 'pass_traj*' |wc -l`
done

# run resampling and check completion
qsub submit_resample.sh $1 $k > GKTL_log.txt
  
x=`find $1 -name 'pass_resample*' |wc -l`
while [ $x -ne $k ]
do
sleep 120
x=`find $1 -name 'pass_resample*' |wc -l`
done 

rm -r *.sh.o*
rm -r *.sh.e*

done

qsub submit_wrap.sh $1 > GKTL_log.txt

x=`find $1 -name 'pass_wrap' |wc -l`
while [ $x -ne 1 ]
do
sleep 120
x=`find $1 -name 'pass_wrap' |wc -l`
done

rm -r *.sh.o*
rm -r *.sh.e*
rm GKTL_log.txt

}

echo 'K_10_a'
echo '---'
run_exp 'K_10_a' 10 512 'initial_0.7_6'

