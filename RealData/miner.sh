#!/bin/bash

generatorFolder="../DataGenerator"
generatorPath="../DataGenerator/generate.sh"
logPath="../SyntheticData/testTraces.log"
xesPath="../SyntheticData/testTraces.xes"
miningWrapper="miningWrapper.py"
minerPath="../PromTools/miner.sh"
minerScript="../PromTools/alphaMiner.txt"
pnmlPath="../SyntheticData/testModel.pnml"
pnmlConverterPath="../ConversionScripts/Pnml2Graphml.py"
graphmlPath="../SyntheticData/testModel.graphml"
subgraphGeneratorPath="./GenerateTraceSubgraphs.py"
subdueLogPath="./test.g"

#generate a model containing appr. 20 activities, and generate 1000 traces from it
cd $generatorFolder
sh $generatorPath 20 1000 $logPath $xesPath
cd "../Testing/"

#mine the ground-truth model from the generated data
cd "../PromTools/"
python $miningWrapper -miner=alpha -ifile=$xesPath -ofile=$pnmlPath

cd "../Testing/"
sh $minerPath -f $minerScript

#convert the mined pnml model to graphml
python $pnmlConverterPath $pnmlPath $graphmlPath
#generate sub-graphs from the mined graphml model
python $subgraphGeneratorPath $graphmlPath $logPath $subdueLogPath
#call subdue/gbad


