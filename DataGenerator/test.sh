numActivites="20"
echo Building process model with appr $numActivites activities...
python ModelGenerator.py -n=$numActivites -a=1 -config=generator.config -file=model.txt
python ModelConverter.py model.txt testModel.graphml
python DataGenerator.py testModel.graphml -n=1000 -ofile=testTraces.g