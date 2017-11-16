#!/bin/sh

for i in {1..60}; do
	modelDir=../Datasets/Test_0/T$i
	for j in $(seq 0 2 20); do
		testDir="$modelDir/anomaly_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done
done
