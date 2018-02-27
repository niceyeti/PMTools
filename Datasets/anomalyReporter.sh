#!/bin/sh

#Re-runs anomaly detector for various values of bayes threshold, for this dataset

rootFolder=$1
#rootFolder="Test_1"
echo executing from $rootFolder

cd $rootFolder

for i in $(seq 1 60); do
	thisDir="T$i"
	cd $thisDir
	
	for thetaIncrement in $(seq 5 9); do
		thetaDir=theta_$thetaIncrement
		cd $thetaDir
		#Toggle this line in and out to re-run bayes param value of 0.0; this is needed because 1.0 in the loop below wraps to 0.0 (just in file-naming)
		#python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=0.0 --bayesOnly
		for increment in $(seq 0 2 98); do
			threshold=$(awk "BEGIN {print $increment / 100}")
			echo "threshold: $threshold"
			python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=$threshold --bayesOnly
		done
		cd ..
	done

	#make the logs at various theta-trace values, in increments of 0.1
	for thetaIncrement in $(seq 0 2 20); do
		thetaDir=anomaly_$thetaIncrement
		cd $thetaDir
		#Toggle this line in and out to re-run bayes param value of 0.0; this is needed because 1.0 in the loop below wraps to 0.0 (just in file-naming)
		#python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=0.0 --bayesOnly
		#python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=0.0 --bayesOnly
		for increment in $(seq 0 2 98); do
			threshold=$(awk "BEGIN {print $increment / 100}")
			echo "threshold: $threshold"
			python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=$threshold --bayesOnly
		done
		cd ..
	done
	
	#make the logs at various theta-trace values, in increments of 0.1
	for thetaIncrement in $(seq 25 5 50); do
		thetaDir=anomaly_$thetaIncrement
		cd $thetaDir
		#Toggle this line in and out to re-run bayes param value of 0.0; this is needed because 1.0 in the loop below wraps to 0.0 (just in file-naming)
		#python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=0.0 --bayesOnly
		#python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=0.0 --bayesOnly
		for increment in $(seq 0 2 98); do
			threshold=$(awk "BEGIN {print $increment / 100}")
			echo "threshold: $threshold"
			python ../../../../Testing/AnomalyReporter.py -gbadResult=gbadResult.txt -logFile=testTraces.log -resultFile=anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=markovModel.py -traceGraphs=traceGraphs.py -bayesThreshold=$threshold --bayesOnly
		done
		cd ..
	done

	cd ..
	pwd
done
