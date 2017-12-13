#!/bin/sh

#for i in {1..60}; do
for i in $(seq 31 1 31); do
	modelDir=../Datasets/Test_1_Retest/T$i
	for j in $(seq 6 1 6); do
		testDir="$modelDir/theta_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done
done
