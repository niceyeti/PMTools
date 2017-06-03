#This is the complete script for generating a model, converting it to something usable, and then
#generating data from it. In all likelihood only components will be used for research, re-testing
#models instead of generating new ones for every test.

if [ $# -lt 5 ]; then
	echo "ERROR: Insufficient number of parameters passed to generate.sh"
	exit
fi

echo Generating model with $1 activities and by which $2 traces will be generated and stored.
numActivites=$1
numTraces=$2
logPath=$3
xesPath=$4
graphmlPath=$5
addNoise="false"
if [ $# -gt 5 ]; then
	if [[ $6 == "--noise="* ]]; then
		noisedLogPath=$(echo $6 | cut -f2 -d=)
		addNoise="true"
	fi
fi

noiseRate="0.0"
for var in "$@"; do
	#get the noise rate, if any
	if [[ $var == "--noiseRate="* ]]; then
		noiseRate=$(echo $var | cut -f2 -d=)
	fi
done

echo Building process model with appr $numActivites activities...
#build the model, using Bezerra's algorithm
python ModelGenerator.py -n=$numActivites -a=1 -config=generator.config -file=model.txt -graph=$graphmlPath
#convert the generated model to transferrable graphml
#python ModelConverter.py model.txt $graphmlPath
#generate stochastic walk data from the model
python DataGenerator.py $graphmlPath -n=$numTraces -ofile=$logPath -noiseRate=$noiseRate

sourceLog=$logPath
#add noise if --noise passed
if [[ $addNoise == "true" ]]; then
	echo ADDING NOISE INNER s$logPath s$noisedLogPath
	python LogNoiser.py $logPath $noisedLogPath
	sourceLog=$noisedLogPath
fi

#convert synthetic data to xes format for process mining
python SynData2Xes.py -ifile=$sourceLog -ofile=$xesPath
