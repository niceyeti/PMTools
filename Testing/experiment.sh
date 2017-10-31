#!/bin/sh

for i in {1..60}; do
	modelDir=../Datasets/Test/T$i
	for j in {5..9}; do
		testDir="$modelDir/theta_$j"
		echo $testDir
		sh completeTest.sh --deleteSubs --recurse=200 --dataDir=$testDir
	done
done
