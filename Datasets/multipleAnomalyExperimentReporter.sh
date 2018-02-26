#!/bin/sh

#Re-runs anomaly detector for various values of bayes threshold, for this dataset

rootFolder=$1
echo executing from $rootFolder

cd $rootFolder

for i in {0,1,2,4,8,16,32}; do
#for i in {8,16}; do
	thisDir="A$i"
	cd $thisDir
	
	for j in $(seq 1 30); do
		testDir="T$j"
		cd $testDir

		for thetaIncrement in $(seq 0 2 98); do
			threshold=$(awk "BEGIN {print $thetaIncrement / 100}")
			echo "threshold: $threshold"
			python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=$threshold --bayesOnly
		done
		
		cd ..
	done
	
	cd ..
	pwd
done
