#!/bin/bash

#This takes an optional "-resultDest=" param denoting the location of a result folder, relative to '.' (the 'Testing' folder)

generatorFolder="../DataGenerator"
generatorPath="../DataGenerator/generate.sh"
logPath="../SyntheticData/testTraces.log"
noisedLogPath="../SyntheticData/noisedTraces.log"
xesPath="../SyntheticData/testTraces.xes"
syntheticGraphmlPath="../SyntheticData/syntheticModel.graphml"
syntheticPngPath="../SyntheticData/syntheticModel.png"

minerName="inductive" #the chosen miner: inductive, alpha, or heuristic
miningWrapper="miningWrapper.py"
minerPath="../scripts/PromTools/miner.sh"
classifierString="Activity"

logNoiser="./LogNoiser.py"
logCompressor="./SubdueLogCompressor.py"
pnmlConverterPath="../ConversionScripts/Pnml2Graphml.py"
subgraphGeneratorPath="./GenerateTraceSubgraphs.py"
pnmlPath="../SyntheticData/testModel.pnml"
minedGraphmlPath="../SyntheticData/minedModel.graphml"
minedPngPath="../SyntheticData/minedModel.png"
subdueLogPath="../SyntheticData/test.g"
compressedLog="../SyntheticData/compressed.g"
gbadFsmLogPath="../SyntheticData/test_fsm.g"

#gbad/subdue experimental parameters. these may become bloated, so I may need to manage them elsewhere, eg a config file
#gbadMdlParam="0.50"

#set the path to the gbad and subdue executables depending on which os we're running under
gbadMdlPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-mdl.exe"
gbadFsmPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-fsm.exe"
subduePath="../../subdue-5.2.2/subdue-5.2.2/src/subdue.exe"
subdueFolder="../../subdue-5.2.2/subdue-5.2.2/src/subdue.exe"
osName=$(uname)
platform="$osName"
#echo OS name $platform
if [ "$platform" = "Linux" ]; then	#reset paths if running linux
	echo resetting paths for $platform
	gbadMdlPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-mdl_linux"
	#gbadMdlPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad"
	gbadFsmPath="../../gbad-tool-kit_3.2/gbad-tool-kit_3.2/bin/gbad-fsm_linux"
	subduePath="../../subdue-5.2.2/subdue-5.2.2/src/subdue_linux"
	subdueFolder="../../subdue-5.2.2/subdue-5.2.2/src/"
fi

#get the command line arg switches, if any
generateData="false"
deleteSubstructures="false"
recursiveIterations="0"
resultDestFolder="NULL"
addNoise="false"
for var in "$@"; do
	#echo $var
	#detect the data generation bool
	if [[ "$var" == "--generate" ]]; then
		generateData="true"
	fi
	#get the number of recursive iterations, if any
	if [[ $var == "--recurse="* ]]; then
		recursiveIterations=$(echo $var | cut -f2 -d=)
		echo "Running for $recursiveIterations iterations"
	fi
	#detect the substructure deletion flag (only meaningful if --recurse is passed as well)
	if [[ "$var" == "--deleteSubs" ]]; then
		deleteSubstructures="true"
	fi
	if [[ "$var" == "--noise" ]]; then
		addNoise="true"
	fi 
	#detect if results should be stored off to some home directory
	if [[ "$var" == "--resultDest="* ]]; then
		resultDestFolder=$(echo $var | cut -f2 -d=)
		echo Running with resulfolder $resultDestFolder
	fi
done

if [ $generateData = "true" ]; then
	###############################################################################
	##Generate a model containing appr. 20 activities, and generate 1000 traces from it.
	cd "../DataGenerator"
	if [[ $addNoise == "true" ]]; then
		echo ADDING NOISE
		sh ./generate.sh 20 200 $logPath $xesPath $syntheticGraphmlPath --noise=$noisedLogPath
	else
		sh ./generate.sh 20 200 $logPath $xesPath $syntheticGraphmlPath
	fi

	###############################################################################
	##Prep the java script to be passed to the ProM java cli; note the path parameters to the miningWrapper are relative to the ProM directory
	cd "../PromTools"
	#Note that the literal ifile/ofile params (testTraces.txt and testModel.pnml) are correct; these are the string params to the mining script generator, not actual file params. 
	python $miningWrapper -miner=$minerName -ifile=testTraces.xes -ofile=testModel.pnml -classifierString=$classifierString
	#Copy everything over to the ProM environment; simpler to run everything from there.
	minerScript="$minerName"Miner.js
	promMinerPath=../../ProM/"$minerScript"
	cp $minerScript $promMinerPath
	cp $xesPath ../../ProM/testTraces.xes
	cp ./miner.sh ../../ProM/miner.sh
	
	###############################################################################
	##Run a process miner to get an approximation of the ground-truth model. Runs a miner with the greatest generalization, least precision.
	cd "../../ProM"
	sh ./miner.sh -f $minerScript
	#copy the mined model back to the SyntheticData folder
	cp ./testModel.pnml ../scripts/SyntheticData/testModel.pnml
	cd "../scripts/Testing"
	#Convert the mined pnml model to graphml
	python $pnmlConverterPath $pnmlPath $minedGraphmlPath --show
	
	################################################################################
	##anomalize the model???
	#
	################################################################################
	##Generate sub-graphs from the mined graphml model
	python $subgraphGeneratorPath $minedGraphmlPath $logPath $subdueLogPath --gbad
	###Added step: gbad-fsm requires a undirected edges declarations, so take the subueLog and just convert the 'd ' edge declarations to 'u '
	###python ../ConversionScripts/SubdueLogToGbadFsm.py $subdueLogPath $gbadFsmLogPath
fi

##############################################################################
#Call gbad on the generated traces (note: gbad-prob->insertions, gbad-mdl->modifications/substitutions, gbad-mps->deletions)
#GBAD-FSM: mps param: closer the value to 0.0, the less change one is willing to accept as anomalous. mst: minimum support thresh, best structure must be included in at least *mst* XP transactions
mdlResult="../TestResults/mdlResult.txt"
mpsResult="../TestResults/mpsResult.txt"
probResult="../TestResults/probResult.txt"
fsmResult="../TestResults/fsmResult.txt"
#fsmTemp="../TestResults/fsmPostProced.txt"
gbadResult="../TestResults/gbadResult.txt"
anomalyFile="../TestResults/anomalyResult.txt"

##clear any previous results
#cat /dev/null > $mdlResult
#cat /dev/null > $mpsResult
#cat /dev/null > $probResult
#cat /dev/null > $fsmResult
#
gbadThreshold="0.1" #the best performance always seems to be about 0.3; I need to justify this
numTraces="200"

echo Running gbad-mdl from $gbadMdlPath
#numerical params: for both mdl and mps, 0.2 to 0.5 have worked well, at least for a log with 9/200 anomalous rates. Values of 0.4 or greater risk extemely long running times.
$gbadMdlPath -mdl $gbadThreshold $subdueLogPath > $mdlResult
#echo Running gbad-mps from $gbadMdlPath
#$gbadMdlPath -mps $gbadThreshold $subdueLogPath > $mpsResult
#echo Running gbad-prob from $gbadMdlPath
#$gbadMdlPath -prob 2 $subdueLogPath > $probResult

cat /dev/null > "dendrogram.txt"
#run recursive-compression gbad, building a dendrogram of the subgraphs of the graph
if [ $recursiveIterations -gt 0 ]; then
	cp $mdlResult lastMdlResult.txt
	#compress the best substructure and re-run; all gbad versions should output the same best-substructure, so using mdlResult.txt's ought to be fine
	python $logCompressor $subdueLogPath lastMdlResult.txt $compressedLog name=SUB_init --deleteSubs=$deleteSubstructures
	for i in $(seq 0 $recursiveIterations); do
		echo Compression iteration $i
		echo Re-running gbad mdl with threshold $gbadThreshold
		$gbadMdlPath -mdl $gbadThreshold $compressedLog > lastMdlResult.txt
		cat lastMdlResult.txt >> $mdlResult

		#recompress the best substructure and re-run, using the previous compressed log as input and then outputting to it as well
		python $logCompressor $compressedLog lastMdlResult.txt $compressedLog name=SUB$i --deleteSubs=$deleteSubstructures
		#break loop once an empty log is encountered
		emptinessTest=$(cat $compressedLog)
		if [[ -z $emptinessTest ]]; then
			break
		fi
	done
fi

#REMEMBER: Once anomalies are obtained, they can be used to drive some search for the structural characteristics shared amongst
#themselves, and also do not share amongst the community of 'normal' traces, such that we find the ground truth of the anomalies (eg, some edge
#or vertex. Then you could search based on that property to discover other anomalies a priori/explicitly.

##Concat the gbad results into a single file so they are easier to analyze at once
cat $mdlResult > $gbadResult
cat $mpsResult >> $gbadResult
cat $probResult >> $gbadResult
#cat $fsmResult >> $gbadResult

python ./AnomalyReporter.py -gbadResult=$gbadResult -logFile=$logPath -resultFile=$anomalyFile --dendrogram=dendrogram.txt --dendrogramThreshold=0.18

#if resultDestFolder param was passed, copy all result files and other artifacts to the dest folder param
if [ $resultDestFolder != "NULL" ]; then
	cp $logPath "$resultDestFolder/testTraces.log"
	cp $xesPath "$resultDestFolder/testTraces.xes"
	cp $syntheticGraphmlPath "$resultDestFolder/syntheticModel.graphml"
	cp $syntheticPngPath "$resultDestFolder/syntheticModel.png"
	cp $pnmlPath "$resultDestFolder/minedModel.pnml"
	cp $minedGraphmlPath "$resultDestFolder/minedModel.graphml"
	cp $minedPngPath "$resultDestFolder/minedModel.png"
	cp $subdueLogPath "$resultDestFolder/test.g"
	cp $compressedLog "$resultDestFolder/compressed.g"
	cp $gbadFsmLogPath "$resultDestFolder/test_fsm.g"
	cp $mdlResult "$resultDestFolder/mdlResult.txt"
	cp $mpsResult "$resultDestFolder/mpsResult.txt"
	cp $probResult "$resultDestFolder/probResult.txt"
	cp $fsmResult "$resultDestFolder/fsmResult.txt"
	cp $gbadResult "$resultDestFolder/gbadResult.txt"
	cp $anomalyFile "$resultDestFolder/anomalyResult.txt"
	cp dendrogram.txt "$resultDestFolder/dendrogram.txt"
fi

