#!/bin/sh

#for i in {1..60}; do
for i in $(seq 60); do
	modelDir=../Datasets/Test_0_Retest/T$i
	for j in $(seq 5 9); do
		testDir="$modelDir/theta_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done
done
