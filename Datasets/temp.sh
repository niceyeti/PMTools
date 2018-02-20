#Adapted from datasetGenerator.sh, just to generate more data for different theta_anomaly values, while fixing theta_trace to 0.5.

#Script for generating a dataset of models containing a range of anomalies (in quantity).

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

modelCount=30
anomalyTheta=0.05
thetaTrace=0.50
numAnomalies=16
anomDir="A$numAnomalies"
cd $anomDir
#make the logs at various theta-trace values, in increments of 0.2
modelDir="T14"
chmod ugo+rwx $modelDir
cd $modelDir
echo HERE
pwd
#if [ ! -f traceDistribution.png ]; then #makes new data files in directories for which generation previously failed
echo making $logPath in $(pwd) and anomaly theta $anomalyTheta
python ../../../../DataGenerator/ModelGenerator.py -n=$numActivities -a=$numAnomalies -config=../../anomalousModelExpt.config -file=$modelPath -graph=$syntheticGraphmlPath -quiet --loopUntilKAnomalies
python ../../../../DataGenerator/DataGenerator.py $syntheticGraphmlPath -n=$numTraces -ofile=$logPath --thetaAnomaly=$anomalyTheta --thetaTrace=$thetaTrace


