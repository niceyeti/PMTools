#!/bin/sh

#for i in {1..60}; do
for i in $(seq 57 1 57); do
	modelDir=../Datasets/Test_1/T$i
	for j in $(seq 5 9); do
		testDir="$modelDir/theta_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done
done
