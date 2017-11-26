#!/bin/sh

#Loops over the models folders (Txx) and runs the compression method on each of the anomaly_x folder's logs.

#for i in {1..60}; do
for i in $(seq 36 1 60); do
	modelDir=../Datasets/Test_1/T$i
	testDir="$modelDir/anomaly_0"
	echo $testDir
	sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir

	#for j in $(seq 0 2 20); do
	#	testDir="$modelDir/anomaly_$j"
	#	echo $testDir
	#	sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	#done
done

