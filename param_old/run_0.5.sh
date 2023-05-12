#!/bin/bash

# Function to run an experiment
# Arguments -
# 1 - Directory to run experiment in
# 2 - Value of selection coefficient to be used
# 3 - Number of trajectories to be run
# 4 - Directory of initial states
# 5 - Starting iteration for an experiment (optional - to restart from crash) 

run_exp(){

# check restart argument and default to 1 if not passed
iter=${5:-1}

# clear slurm logs
rm -r *.sh.o*
rm -r *.sh.e*
rm GKTL_log.txt


# run GKTL_init for new experiments 
if [ $iter -eq 1 ]
then

echo "starting new experiment"
# create directory for experiment
rm -r $1
mkdir $1

# run GKTL_init
pass=0
while [ $pass -ne 1 ]
do
if qsub submit_init.sh $1 $2 $3 $4 > GKTL_log.txt; then
pass=1
else
sleep 1
fi
done

else

echo "starting experiment from iteration $iter"
rm -r $1/pass_traj*
rm -r $1/traj_new*
fi

# proceed only if pass_init file is found in directory
x=`find $1 -name 'pass_init' |wc -l`
while [ $x -ne 1 ]
do
sleep 60
x=`find $1 -name 'pass_init' |wc -l`
done


## end of initialisation - iteration begin

n=40 # number of parallel trajectories

# loop over algorithm iterations
for (( k = iter; k <= 16 ; k++ ))
do

echo $k


# submit jobs - n jobs at a time
c=1
x_prev=0
for (( i = 1; i <= $n; i++ )) 
do 

pass=0
while [ $pass -ne 1 ]
do
echo $c
if qsub submit_traj_ser.sh $1 $i $k > GKTL_log.txt; then
#echo $c
c=$((c+1))
pass=1
else
sleep 1
fi
done
done

while [ $c -le $3 ]
do
x=`find $1 -name 'pass_traj*' |wc -l`

for (( i = 0; i < x-x_prev; i++ ))
do
if [ $c -le $3 ]
then

pass=0
while [ $pass -ne 1 ]
do
echo $c
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

# wait till all trajectory runs have completed
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

# perform final computations and cleanup with GKTL_wrap

pass=0
while [ $pass -ne 1 ]
do
if qsub submit_wrap.sh $1 > GKTL_log.txt; then
pass=1
else
sleep 1
fi
done

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



# Experiment list with details

echo 'K_50_even'
#echo '---'
#run_exp 'K_50_even' 50 512 'initial_summer_0.5_6' 11

echo 'K_40_a'
#echo '---'
#run_exp 'K_40_a' 40 512 'initial_summer_0.5_6' 16

echo 'K_20_b'
#echo '---'
#run_exp 'K_20_b' 20 512 'initial_summer_0.5_6' 16

echo 'K_40_i'
#echo '---'
#run_exp 'K_40_i' 40 512 'initial_summer_0.5_6' 13

echo 'K_30_e'
#echo '---'
#run_exp 'K_30_e' 30 512 'initial_summer_0.5_6'

echo 'K_20_e'
#echo '---'
#run_exp 'K_20_e' 20 512 'initial_summer_0.5_6'

echo 'K_10_e'
#echo '---'
#run_exp 'K_10_e' 10 512 'initial_summer_0.5_6'

