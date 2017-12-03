#!/bin/sh

#Loops over the models folders (Txx) and runs the compression method on each of the anomaly_x folder's logs.

#for i in {1..60}; do
for i in $(seq 60); do
	modelDir=../Datasets/Test_0_Retest/T$i
	testDir="$modelDir/anomaly_0"
	echo $testDir
	#sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir

	for j in $(seq 0 2 20); do
		testDir="$modelDir/anomaly_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done

	#additional anomaly_theta testing, in increments of 0.05, up to 0.50
	for j in $(seq 25 5 50); do
		testDir="$modelDir/anomaly_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done

done
