#!/bin/sh

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
subdueLogPath="./test.g"

#gbad/subdue experimental parameters. these may become bloated, so I may need to manage them elsewhere, eg a config file
gbadMdlParam="0.50"

#set the path to the gbad and subdue executables depending on which os we're runnin
gbadMdlPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-mdl.exe"
gbadFsmPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-fsm.exe"
subduePath="../../subdue-5.2.2/subdue-5.2.2/src/subdue.exe"
subdueFolder="../../subdue-5.2.2/subdue-5.2.2/src/subdue.exe"
osName=$(uname)
platform="$osName"
#echo OS name $platform
if [ "$platform" = "Linux" ]; then	#reset paths if running linux; DONT use if-else for the os detection, as cygwin doesn't support `uname` command
	echo resetting paths for $platform
	gbadMdlPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-mdl_linux"
	gbadFsmPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-fsm_linux"
	subduePath="../../subdue-5.2.2/subdue-5.2.2/src/subdue_linux"
	subdueFolder="../../subdue-5.2.2/subdue-5.2.2/src/"
fi

###Generate a model containing appr. 20 activities, and generate 1000 traces from it
#cd "../DataGenerator"
#sh ./generate.sh 20 1000 $logPath $xesPath $syntheticGraphmlPath
#
##Prep the java script to be passed to the ProM java cli; note the path parameters to the miningWrapper are relative to the ProM directory
#cd "../PromTools"
#python $miningWrapper -miner=$minerName -ifile=testTraces.xes -ofile=testModel.pnml -classifierString=$classifierString
##copy everything over to the ProM environment; simpler to run everything from there
#minerScript="$minerName"Miner.js
#promMinerPath=../../ProM/"$minerScript"
#echo Prom miner path: $promMinerPath
#cp $minerScript $promMinerPath
#cp $xesPath ../../ProM/testTraces.xes
#cp ./miner.sh ../../ProM/miner.sh
#
#
#
#
##Run the process miner to get an approximate ground-truth model
#cd "../../ProM"
#sh ./miner.sh -f $minerScript
##copy the mined model back to the SyntheticData folder
#cp ./testModel.pnml ../scripts/SyntheticData/testModel.pnml
#
#cd "../scripts/Testing"
##Convert the mined pnml model to graphml
#python $pnmlConverterPath $pnmlPath $minedGraphmlPath --show

#anomalize the model???

##generate sub-graphs from the mined graphml model
#python $subgraphGeneratorPath $minedGraphmlPath $logPath $subdueLogPath --gbad

#call gbad on the generated traces (note: gbad-prob->insertions, gbad-mdl->modifications, gbad-mps->deletions)
#$gbadMdlPath -mdl 0.50 $subdueLogPath

#GBAD-FSM: mps param: closer the value to 0.0, the less change one is willing to accept as anomalous. mst: minimum support thresh, best structure must be included in at least mst XP transactions
$gbadMdlPath -mdl 0.9 $subdueLogPath
$gbadMdlPath -mps 0.9 $subdueLogPath
$gbadFsmPath -mps 0.1 -mst 20 $subdueLogPath




