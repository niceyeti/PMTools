#Generates a single model and its log with a specified number of anomalous structures, and the trace data from it
#In this experiment, theta_trace is fixed, and so is the trace components of theta_anomaly. Instead we
#generate a model with a fixed number of anomalies, which is done by generating models until one is generated
#that satisfied these constraints.


if [ $# -lt 6 ]; then
	echo "ERROR: Insufficient number of parameters passed to generateAnomalousModel.sh"
	exit
fi

echo Generating model with $1 anomalous structures and by which $2 traces will be generated and stored.
numAnomalies=$1
numTraces=$2
logPath=$3
graphmlPath=$4
modelPath=$5
modelConfig=$6
generateTraces="true"

for var in "$@"; do
	#detect the no-trace-generation param
	if [ "$var" = "--noGen" ]; then
		generateTraces="false"
	fi
done

echo Building process model with appr $numActivites activities...
#build the model, using Bezerra's algorithm
python ModelGenerator.py -n=$numActivites -a=$numAnomalies -config=$modelConfig -file=$modelPath -graph=$graphmlPath -quiet
#convert the generated model to transferrable graphml
#python ModelConverter.py model.txt $graphmlPath

if [ $generateTraces = "true" ]; then
	#generate stochastic walk data from the model
	python DataGenerator.py $graphmlPath -n=$numTraces -ofile=$logPath
fi


