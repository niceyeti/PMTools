#!/bin/bash

generatorFolder="../DataGenerator"
generatorPath="../DataGenerator/generate.sh"
syntheticGraphmlPath="../SyntheticData/syntheticModel.graphml"
logPath="../SyntheticData/testTraces.log"
xesPath="../SyntheticData/testTraces.xes"

miningWrapper="miningWrapper.py"
minerPath="../PromTools/miner.sh"
minerScript="../PromTools/inductiveMiner.js"
classifierString="Activity"

pnmlPath="../SyntheticData/testModel.pnml"
pnmlConverterPath="../ConversionScripts/Pnml2Graphml.py"
minedGraphmlPath="../SyntheticData/minedModel.graphml"
subgraphGeneratorPath="./GenerateTraceSubgraphs.py"
subdueLogPath="./test.g"

#Generate a model containing appr. 20 activities, and generate 1000 traces from it
cd "../DataGenerator/"
sh $generatorPath 20 1000 $logPath $xesPath $syntheticGraphmlPath

#Prep the java script to be passed to the ProM java cli
cd "../PromTools/"
python $miningWrapper -miner=inductive -ifile=$xesPath -ofile=$pnmlPath -classifierString=$classifierString

#Run the process miner to get an approximate ground-truth model
cd "../Testing/"
sh $minerPath -f $minerScript

#convert the mined pnml model to graphml
python $pnmlConverterPath $pnmlPath $minedGraphmlPath --show
#generate sub-graphs from the mined graphml model
python $subgraphGeneratorPath $minedGraphmlPath $logPath $subdueLogPath
#call subdue/gbad
