#!/bin/sh

#single purpose script for fixing a file naming issue in the dataset generator: need to call all .log files "testTraces.log"

rootFolder="Test_1"
cd $rootFolder

for i in $(seq 60); do
	thisDir="T$i"
	cd $thisDir
	#make the logs at various theta-trace values, in increments of 0.1
	for thetaIncrement in $(seq 5 9); do
		newDir=theta_$thetaIncrement
		cd $newDir
		#echo $newDir
		#mv "theta_$thetaIncrement.log" testTraces.log
		rm bayesResult_07.txt
		pwd
		cd ..
	done
	
	for thetaIncrement in $(seq 0 2 20); do
		newDir=anomaly_$thetaIncrement
		cd $newDir
		#mv "theta_$thetaIncrement.log" testTraces.log
		rm bayesResult_07.txt
		#echo $newDir
		pwd
		cd ..
	done

	cd ..

	#pwd
done
