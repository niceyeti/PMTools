#Script for generating 60 datasets, each with 1000 traces, outputting each to the passed directory

if [ $# -lt 2 ]; then
	echo "ERROR: Insufficient number of parameters passed to datasetGenerator.sh"
	exit
fi

rootFolder=$1

echo Generating 60 datasets in $rootFolder with 30 activities and by which 1000 traces will be generated and stored.

logPath="$rootFolder/testTraces.log"
noisedLog="$rootFolder/noisedTraces.log"
xesPath="$rootFolder/testTraces.xes"
syntheticGraphmlPath="$rootFolder/syntheticModel.graphml"

cd $rootFolder

for i in $(seq 60); do
	mkdir "t$i"
	#loop and create the sixty datasets, each in their own folder
	#sh ..DataGenerator/generate.sh 30 1000 $logPath $syntheticGraphmlPath
done
