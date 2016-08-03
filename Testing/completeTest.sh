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

#gbad/subdue experimental parameters. these may become bloated, so I may need to manage them elsewhere, eg a config file
gbadMdlParam="0.001"

#set the path to the gbad and subdue executables depending on which os we're runnin
gbadMdlPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-mdl.exe"
gbadFsmPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-fsm.exe"
subduePath="../../subdue-5.2.2/subdue-5.2.2/src/subdue.exe"
subdueFolder="../../subdue-5.2.2/subdue-5.2.2/src/subdue.exe"
osName=$(uname)
platform="$osName"
echo OS name $platform
if [ "$platform" = "Linux" ]; then	#reset paths if running linux; DONT use if-else for the os detection, as cygwin doesn't support `uname` command
	echo resetting paths for $platform
	gbadMdlPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-mdl_linux"
	gbadFsmPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-fsm_linux"
	subduePath="../../subdue-5.2.2/subdue-5.2.2/src/subdue_linux"
	subdueFolder="../../subdue-5.2.2/subdue-5.2.2/src/"
fi

##Generate a model containing appr. 20 activities, and generate 1000 traces from it
cd "../DataGenerator"
sh $generatorPath 20 1000 $logPath $xesPath $syntheticGraphmlPath

#Prep the java script to be passed to the ProM java cli; note the path parameters to the miningWrapper are relative to the ProM directory
cd "../PromTools"
python $miningWrapper -miner=inductive -ifile=testTraces.xes -ofile=testModel.pnml -classifierString=$classifierString
#copy everything over to the ProM environment for simplicity
cp ./inductiveMiner.js ../../ProM/inductiveMiner.js
cp testTraces.xes ../../ProM/testTraces.xes
cp ../PromTools/miner.sh ../../ProM/miner.sh

#Run the process miner to get an approximate ground-truth model
cd "../../ProM"
sh ./miner.sh -f inductiveMiner.js
cp ./testModel.pnml ../scripts/SyntheticData/testModel.pnml

#convert the mined pnml model to graphml
cd "../scripts/Testing"
python $pnmlConverterPath $pnmlPath $minedGraphmlPath --show
#generate sub-graphs from the mined graphml model
python $subgraphGeneratorPath $minedGraphmlPath $logPath $subdueLogPath --gbad

#call gbad on the generated traces
$gbadMdlPath -mdl $gbadMdlParam $subdueLogPath



