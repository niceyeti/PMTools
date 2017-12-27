#Single purpose script for verifying all result files are in place, checking integrity

rootFolder="Test_1_Retest"
cd $rootFolder

for i in $(seq 60); do
	modelDir="T$i"
	#cd $modelDir
	#test the sampling algorithm at different theta values
	for thetaIncrement in $(seq 5 9); do
		newDir=theta_$thetaIncrement
		python SampleAlgoTest.py --indir=$modelDir/$newDir #SampleAlgoTest.py must be run from /Datasets/
	done

	#for thetaIncrement in $(seq 0 2 20); do
	#	newDir=anomaly_$thetaIncrement
	#	count=$(ls $newDir/bayesResult* | wc -l)
	#	echo $thisDir/$newDir count is $count		
	#done
	#
	#for thetaIncrement in $(seq 25 5 50); do
	#	newDir=anomaly_$thetaIncrement
	#	count=$(ls $newDir/bayesResult* | wc -l)
	#	echo $thisDir/$newDir count is $count
	#done
	
	cd ..
	#pwd
done
