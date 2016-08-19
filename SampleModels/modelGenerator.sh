#!/bin/sh

#A script for generating k process models, each of which is then process-mined
#and used to generate 1000 traces. 1000 may be overkill, and if so, it is possible to discard some.
#Each model gets its own folder, containing:
#	-groundTruth.graphml : the randomly generated process model according to Bezerra's algorithm
#	-traces.log : A set of traces generated from the groundTruth.graphml via stochastic walks
#	-

generatorFolder="../DataGenerator"
generatorPath="../DataGenerator/generate.sh"
logPath="../SyntheticData/testTraces.log"
xesPath="../SyntheticData/testTraces.xes"
syntheticGraphmlPath="../SyntheticData/syntheticModel.graphml"

minerName="inductive" #the chosen miner: inductive, alpha, or heuristic
miningWrapper="miningWrapper.py"
minerPath="../scripts/PromTools/miner.sh"
classifierString="Activity"

pnmlPath="../SyntheticData/testModel.pnml"
pnmlConverterPath="../ConversionScripts/Pnml2Graphml.py"
minedGraphmlPath="../SyntheticData/minedModel.graphml"
subgraphGeneratorPath="./GenerateTraceSubgraphs.py"

##Generate a model containing appr. 20 activities, and generate 1000 traces from it
for i in [1 .. 50] do:
	$logPath = 


	cd "../DataGenerator"
	sh ./generate.sh 20 1000 $logPath $xesPath $syntheticGraphmlPath


#Prep the java script to be passed to the ProM java cli; note the path parameters to the miningWrapper are relative to the ProM directory
cd "../PromTools"
python $miningWrapper -miner=$minerName -ifile=testTraces.xes -ofile=testModel.pnml -classifierString=$classifierString
#copy everything over to the ProM environment; simpler to run everything from there
minerScript="$minerName"Miner.js
promMinerPath=../../ProM/"$minerScript"
echo Prom miner path: $promMinerPath
cp $minerScript $promMinerPath
cp $xesPath ../../ProM/testTraces.xes
cp ./miner.sh ../../ProM/miner.sh




#Run the process miner to get an approximation of the ground-truth model
cd "../../ProM"
sh ./miner.sh -f $minerScript
#copy the mined model back to the SyntheticData folder
cp ./testModel.pnml ../scripts/SyntheticData/testModel.pnml

cd "../scripts/Testing"
#Convert the mined pnml model to graphml
python $pnmlConverterPath $pnmlPath $minedGraphmlPath --show

#anomalize the model???

##generate sub-graphs from the mined graphml model
python $subgraphGeneratorPath $minedGraphmlPath $logPath $subdueLogPath --gbad

