#!/bin/sh
#single purpose script for fixing a file naming issue in the dataset generator: need to call all .log files "testTraces.log"

rootFolder="Test_1_Retest"
cd $rootFolder

for i in $(seq 60); do
	thisDir="T$i"
	cd $thisDir
	#make the logs at various theta-trace values, in increments of 0.1
	for thetaIncrement in $(seq 5 9); do
		newDir=theta_$thetaIncrement
		cd $newDir
		#mv "theta_$thetaIncrement.log" testTraces.log
		#rm bayesResult_07.txt
		rm *
		pwd
		cd ..
		#rmdir $newDir
	done
	
	for thetaIncrement in $(seq 0 2 20); do
		newDir=anomaly_$thetaIncrement
		cd $newDir
		#mv "theta_$thetaIncrement.log" testTraces.log
		#rm bayesResult_07.txt
		#echo $newDir
		rm *
		pwd
		cd ..
		#rmdir $newDir		
	done
	
	for thetaIncrement in $(seq 25 5 50); do
		newDir=anomaly_$thetaIncrement
		cd $newDir
		#mv "theta_$thetaIncrement.log" testTraces.log
		#rm bayesResult_07.txt
		#echo $newDir
		rm *
		pwd
		cd ..
		#rmdir $newDir		
	done
	
	cd ..
	#pwd
done
