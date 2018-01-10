#Single purpose script for verifying all result files are in place, checking integrity

rootFolder="Test_0_Retest"

for i in $(seq 19 19); do
	modelDir="T$i"
	#cd $modelDir
	#test the sampling algorithm at different theta values
	for thetaIncrement in $(seq 5 9); do
		logDir=theta_$thetaIncrement
		python SampleAlgoTest.py --indir=$rootFolder\\$modelDir\\$logDir #SampleAlgoTest.py must be run from /Datasets/
	done

	#for thetaIncrement in $(seq 0 2 20); do
	#	logDir=anomaly_$thetaIncrement
	#	python SampleAlgoTest.py --indir=$rootFolder\\$modelDir\\$logDir #SampleAlgoTest.py must be run from /Datasets/
	#done
	#
	#for thetaIncrement in $(seq 25 5 50); do
	#	logDir=anomaly_$thetaIncrement
	#	python SampleAlgoTest.py --indir=$rootFolder\\$modelDir\\$logDir #SampleAlgoTest.py must be run from /Datasets/
	#done

	#cd ..
	#pwd
done
