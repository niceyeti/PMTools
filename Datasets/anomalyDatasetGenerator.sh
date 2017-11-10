#Adapted from datasetGenerator.sh, just to generate more data for different theta_anomaly values, while fixing theta_trace to 0.5.

if [ $# -lt 1 ]; then
	echo "ERROR: Insufficient number of parameters $# passed to datasetGenerator.sh"
	exit
fi

rootFolder=$1
numActivities="30"
numTraces="1000"

logPath="testTraces.log"
syntheticGraphmlPath="syntheticModel.graphml"
modelPath="model.txt"

cd $rootFolder

modelCount=60

for i in $(seq $modelCount); do
	thisDir="T$i"
	cd ../Datasets/$rootFolder/$thisDir
	#make the logs at various theta-trace values, in increments of 0.2
	for thetaIncrement in $(seq 0 2 20); do
		newDir=anomaly_theta_$thetaIncrement
		mkdir $newDir
		thetaLog="$newDir/$logPath"
		echo making $thetaLog in $(pwd)
		python ../../../DataGenerator/DataGenerator.py $syntheticGraphmlPath -n=$numTraces -ofile=$thetaLog --anomalyTheta=0.$thetaIncrement
	done

	cd ..

	pwd
done
