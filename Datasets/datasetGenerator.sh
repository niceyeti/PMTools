#Script for generating 60 datasets, each with 1000 traces, outputting each to the passed directory

if [ $# -lt 1 ]; then
	echo "ERROR: Insufficient number of parameters $# passed to datasetGenerator.sh"
	exit
fi

rootFolder=$1
numActivities="30"
numTraces="1000"

echo Generating 60 datasets in $rootFolder with $numActivities activities and by which $numTraces traces will be generated and stored.

logPath="testTraces.log"
syntheticGraphmlPath="syntheticModel.graphml"
modelPath="model.txt"

cd $rootFolder

for i in $(seq 10); do
	thisDir="T$i"
	mkdir $thisDir
	cd ../../DataGenerator
	#loop and create sixty datasets, each in their own folder
	sh generate.sh 30 1000 ../Datasets/$rootFolder/$thisDir/$logPath ../Datasets/$rootFolder/$thisDir/$syntheticGraphmlPath ./Datasets/$rootFolder/$thisDir/$modelPath --noGen #Note no xes references; the xes logs are generated later, after possible addition of noise to the base log
	#make the logs at various theta-trace values, in increments of 0.1
	for thetaIncrement in $(seq 5 9); do
		python DataGenerator.py ../Datasets/$rootFolder/$thisDir/$syntheticGraphmlPath -n=$numTraces -ofile=$logPath --thetaTrace=0.$thetaIncrement
	done	

	pwd
	cd ../Datasets/$rootFolder
done
