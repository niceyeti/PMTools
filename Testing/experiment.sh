#!/bin/sh

for i in {16..60}; do
	modelDir=../Datasets/Test_1/T$i
	for j in $(seq 0 2 20); do
		testDir="$modelDir/anomaly_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done
done

