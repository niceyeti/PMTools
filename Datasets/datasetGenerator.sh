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

cd $rootFolder

for i in $(seq 60); do
	thisDir="T$i"
	mkdir $thisDir
	cd ../../DataGenerator
	#loop and create sixty datasets, each in their own folder
	sh generate.sh 30 1000 ../Datasets/$rootFolder/$thisDir/$logPath ../Datasets/$rootFolder/$thisDir/$syntheticGraphmlPath #Note no xes references; the xes logs are generated later, after possible addition of noise to the base log
	pwd
	cd ../Datasets/$rootFolder
done
