#!/bin/sh

#Re-runs anomaly detector for various values of bayes threshold, for this dataset

rootFolder="Test"
cd $rootFolder

for i in $(seq 60); do
	thisDir="T$i"
	cd $thisDir
	#make the logs at various theta-trace values, in increments of 0.1
	for thetaIncrement in $(seq 5 9); do
		thetaDir=theta_$thetaIncrement
		cd $thetaDir
		for increment in $(seq 2 2 20); do
			threshold=$(awk "BEGIN {print $increment / 100}")
			echo "threshold: $threshold"
			python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=$threshold --bayesOnly
		done
		cd ..
	done
	cd ..

	pwd
done
