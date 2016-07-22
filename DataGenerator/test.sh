#This is the complete script for generating a model, converting it to something usable, and then
#generating data from it. In all likelihood only components will be used for research, re-testing
#models instead of generating new ones for every test.

numActivites="20"
logPath="../SyntheticData/testTraces.log"
xesPath="../SyntheticData/testTraces.xes"

echo Building process model with appr $numActivites activities...
#build the model, using Bezerra's algorithm
python ModelGenerator.py -n=$numActivites -a=1 -config=generator.config -file=model.txt
#convert the generated model to transferrable graphml
python ModelConverter.py model.txt testModel.graphml
#generate stochastic walk data from the model
python DataGenerator.py testModel.graphml -n=1000 -ofile=$logPath
#convert synthetic data to xes format for process mining
python SynData2Xes.py -ifile=$logPath -ofile=$xesPath
