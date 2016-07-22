#!/bin/sh
generatorPath="../DataGenerator/generator.sh"
logPath="../SyntheticData/testTraces.log"
xesPath="../SyntheticData/testTraces.xes"
miningWrapper="../PromTools/miningWrapper.py"
minerPath="../PromTools/miner.sh"
minerScript="../PromTools/alphaMiner.txt"
pnmlPath="../SyntheticData/testModel.pnml"
pnmlConverterPath="../ConversionScripts/Pnml2Graphml.py"
graphmlPath="../SyntheticData/testModel.graphml"
subgraphGeneratorPath="./GenerateTraceSubgraphs.py"
subdueLogPath="./test.g"

#generate a model containing appr. 20 activities, and generate 1000 traces from it
sh $generatorPath 20 1000 $logPath $xesPath
#mine the ground-truth model from the generated data
python $miningWrapper -miner=alpha -ifile=$xesPath -ofile=$pnmlPath
sh $minerPath -f $minerScript
#convert the mined pnml model to graphml
python $pnmlConverterPath $pnmlPath $graphmlPath
#generate sub-graphs from the mined graphml model
python $subgraphGeneratorPath $graphmlPath $logPath $subdueLogPath
#call subdue/gbad


