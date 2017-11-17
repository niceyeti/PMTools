#!/bin/sh

for i in {19..60}; do
	modelDir=../Datasets/Test_1/T$i
	for j in $(seq 5 9); do
		testDir="$modelDir/theta_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done
done
