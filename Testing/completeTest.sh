#!/bin/sh

generatorFolder="../DataGenerator"
generatorPath="../DataGenerator/generate.sh"
syntheticGraphmlPath="../SyntheticData/syntheticModel.graphml"
logPath="../SyntheticData/testTraces.log"
xesPath="../SyntheticData/testTraces.xes"

miningWrapper="miningWrapper.py"
minerPath="../scripts/PromTools/miner.sh"
minerScript="../scripts/PromTools/inductiveMiner.js"
classifierString="Activity"

pnmlPath="../SyntheticData/testModel.pnml"
pnmlConverterPath="../ConversionScripts/Pnml2Graphml.py"
minedGraphmlPath="../SyntheticData/minedModel.graphml"
subgraphGeneratorPath="./GenerateTraceSubgraphs.py"
subdueLogPath="./test.g"

#Generate a model containing appr. 20 activities, and generate 1000 traces from it
cd "../DataGenerator"
sh $generatorPath 20 1000 $logPath $xesPath $syntheticGraphmlPath

#Prep the java script to be passed to the ProM java cli; note the path parameters to the miningWrapper are relative to the ProM directory
cd "../PromTools"
python $miningWrapper -miner=inductive -ifile=testTraces.xes -ofile=testModel.pnml -classifierString=$classifierString
#copy everything over to the ProM environment for simplicity
cp ./inductiveMiner.js ../../ProM/inductiveMiner.js
cp $xesPath ../../ProM/testTraces.xes
cp ../PromTools/miner.sh ../../ProM/miner.sh

#Run the process miner to get an approximate ground-truth model
cd "../../ProM"
sh ./miner.sh -f inductiveMiner.js
cp ./testModel.pnml ../scripts/SyntheticData/testModel.pnml

#convert the mined pnml model to graphml
cd "../scripts/Testing"
python $pnmlConverterPath $pnmlPath $minedGraphmlPath --show
#generate sub-graphs from the mined graphml model
python $subgraphGeneratorPath $minedGraphmlPath $logPath $subdueLogPath
#call subdue/gbad
