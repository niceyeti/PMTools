#!/bin/sh

#Loops over the models folders (Txx) and runs the compression method on each of the anomaly_x folder's logs.

#for i in {1..60}; do
for i in {0,1,2,4,8,16}; do
	modelDir=../Datasets/Multiple_Anomaly_Experiment/A$i
	for j in $(seq 1 30); do
		testDir="$modelDir/T$j"
		echo TEST DIR   $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done
done
echo Experiment complete.
