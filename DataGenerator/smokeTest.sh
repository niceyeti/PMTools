#!/bin/bash
for i in `seq 1 2`;
do
	numActivites="45"
	echo Building process model with appr $numActivites activities...
	python ModelGenerator.py -n=$numActivites -a=1 -config=generator.config -file=model.txt
	python ModelConverter.py model.txt testModel.graphml
	python DataGenerator.py testModel.graphml -n=1000 -ofile=testTraces.g
done