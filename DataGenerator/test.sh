#This is the complete script for generating a model, converting it to something usable, and then
#generating data from it. In all likelihood only components will be used for research, re-testing
#models instead of generating new ones for every test.

numActivites="20"
echo Building process model with appr $numActivites activities...
python ModelGenerator.py -n=$numActivites -a=1 -config=generator.config -file=model.txt
python ModelConverter.py model.txt testModel.graphml
python DataGenerator.py testModel.graphml -n=1000 -ofile=testTraces.g