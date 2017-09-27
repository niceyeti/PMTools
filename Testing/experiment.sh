#!/bin/sh

for i in {1..60}; do
	testDir=../Datasets/Sep21/T$i
	sh completeTest.sh --deleteSubs --recurse=100 --dataDir=$testDir
done
