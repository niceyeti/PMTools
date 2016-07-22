#!/bin/sh

#Generates a stochastic process model and then builds synthetic data from it.

numActivites="20"
logPath="../SyntheticData/testTraces.log"
xesPath="../SyntheticData/testTraces.xes"

echo Building process model with appr $numActivites activities...
# 1) build the model, using Bezerra's algorithm
python ModelGenerator.py -n=$numActivites -a=1 -config=generator.config -file=model.txt
# 2) convert the generated model to transferrable graphml
python ModelConverter.py model.txt testModel.graphml
# 3) generate stochastic walk data from the model
python DataGenerator.py testModel.graphml -n=1000 -ofile=$logPath
# 4) convert synthetic data to xes format for process mining
python SynData2Xes.py -ifile=$logPath -ofile=$xesPath
