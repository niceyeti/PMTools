#This is the complete script for generating a model, converting it to something usable, and then
#generating data from it. In all likelihood only components will be used for research, re-testing
#models instead of generating new ones for every test.

if [ $# -ne 5 ]; then
    echo "Incorrect number of parameters"
	return
fi

echo Generating model with $1 activities and from which $2 traces will be stored.
numActivites=$1
numTraces=$2
logPath=$3
xesPath=$4
graphmlPath=$5

echo Building process model with appr $numActivites activities...
#build the model, using Bezerra's algorithm
python ModelGenerator.py -n=$numActivites -a=1 -config=generator.config -file=model.txt
#convert the generated model to transferrable graphml
python ModelConverter.py model.txt $graphmlPath
#generate stochastic walk data from the model
python DataGenerator.py testModel.graphml -n=$numTraces -ofile=$logPath
#convert synthetic data to xes format for process mining
python SynData2Xes.py -ifile=$logPath -ofile=$xesPath
