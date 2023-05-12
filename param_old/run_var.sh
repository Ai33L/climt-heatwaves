#!/bin/bash

rm -r *.sh.o*
rm -r *.sh.e*

rm -r $1
mkdir $1

pass=0
while [ $pass -ne 1 ]
do
if qsub submit_init.sh $1 $2 $3 > GKTL_log.txt; then
pass=1
sleep 1
fi
done

x=`find $1 -name 'link' |wc -l`
while [ $x -ne 1 ]
do
sleep 60
x=`find $1 -name 'link' |wc -l`
done


n=16
for (( k = 1; k <= 16 ; k++ ))

do

echo $k
echo '---'

c=1
step_up=0

while [ $step_up -ne 1 ]
do

scancel -u abel
for (( i = (c-1)*n+1; i <= c*n; i++ )) 
do 

pass=0
while [ $pass -ne 1 ]
do
if qsub submit_traj_ser.sh $1 $i $k > GKTL_log.txt; then
echo $i
pass=1
sleep 1
fi
done

done

tick=1
while [ $tick -ne 4 ]
do
sleep 120
x=`find $1 -name 'traj_new*' |wc -l`
if [ $x -eq $((c*n)) ]
then
if [ $c -eq 32 ]
then
step_up=1
fi
tick=5
c=$((c+1))
else
tick=$((tick+1))
fi

done
done



if [ $k -ne 16 ]
then

pass=0
while [ $pass -ne 1 ]
do
if qsub submit_resample.sh $1 $k > GKTL_log.txt; then
pass=1
sleep 1
fi
done
  
x=`find $1 -name 'resample_log*' |wc -l`
while [ $x -ne $k ]
do
sleep 120
x=`find $1 -name 'resample_log*' |wc -l`
done

else

pass=0
while [ $pass -ne 1 ]
do
if qsub submit_wrap.sh $1 $k > GKTL_log.txt; then
pass=1
sleep 1
fi
done

x=`find $1 -name 'prob' |wc -l`
while [ $x -ne 1 ]
do
sleep 120
x=`find $1 -name 'prob' |wc -l`
done
fi 

rm -r *.sh.o*
rm -r *.sh.e*

done

echo 'done'
