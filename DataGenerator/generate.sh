#This is the complete script for generating a model, converting it to something usable, and then
#generating data from it.

if [ $# -lt 5 ]; then
	echo "ERROR: Insufficient number of parameters passed to generate.sh"
	exit
fi

echo Generating model with $1 activities and by which $2 traces will be generated and stored.
numActivites=$1
numTraces=$2
logPath=$3
graphmlPath=$4
modelPath=$5
generateTraces="true"

for var in "$@"; do
	#detect the no-trace-generation param
	if [ "$var" = "--noGen" ]; then
		generateTraces="false"
	fi
done

echo Building process model with appr $numActivites activities...
#build the model, using Bezerra's algorithm
python ModelGenerator.py -n=$numActivites -a=1 -config=generator.config -file=$modelPath -graph=$graphmlPath -quiet
#convert the generated model to transferrable graphml
#python ModelConverter.py model.txt $graphmlPath

if [ $generateTraces = "true" ]; then
	#generate stochastic walk data from the model
	python DataGenerator.py $graphmlPath -n=$numTraces -ofile=$logPath
fi


