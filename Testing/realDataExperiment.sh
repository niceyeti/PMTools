#!/bin/sh

#For passing an xes file with some real-world data: --xesPath=[path]
#Run as: sh realDataExperiment.sh --deleteSubs --recurse=200 --dataDir=../RealData/results --xesPath="../../../Data/BPI_2015/JUnit 4.12 Software Event Log.xes"



generatorFolder="../DataGenerator"
generatorPath="../DataGenerator/generate.sh"
logPath="$dataDir/testTraces.log"
syntheticGraphmlPath="$dataDir/syntheticModel.graphml"
syntheticModelPath="$dataDir/model.txt"

minerName="inductive" #the chosen miner: inductive, alpha, or heuristic
miningWrapper="miningWrapper.py"
minerPath="../scripts/PromTools/miner.sh"
classifierString="Activity"

logCompressor="./SubdueLogCompressor.py"
pnmlPath="$dataDir/testModel.pnml"
pnmlConverterPath="../ConversionScripts/Pnml2Graphml.py"
minedGraphmlPath="$dataDir/minedModel.graphml"
markovModelPath="$dataDir/markovModel.py"
subgraphGeneratorPath="./GenerateTraceSubgraphs.py"
subdueLogPath="$dataDir/test.g"
traceGraphPath="$dataDir/traceGraphs.py"
compressedLog="$dataDir/compressed.g"
gbadFsmLogPath="$dataDir/test_fsm.g"

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

echo --dataDir param MUST be relative to the context of the completeTest script: $(pwd)
echo Also, it must NOT end with slash
sleep 1

#get the command line arg switches, if any
deleteSubstructures="false"
recursiveIterations="0"
xesPath="empty"
dataDir="../RealData/results"

for var in "$@"; do

	#get the number of recursive iterations, if any
	if [[ $var == "--recurse="* ]]; then
		recursiveIterations=$(echo $var | cut -f2 -d=)
	fi
	#detect the substructure deletion flag (only meaningful if --recurse is passed as well)
	if [ "$var" = "--deleteSubs" ]; then
		deleteSubstructures="true"
	fi

	#get the number of recursive iterations, if any
	if [[ $var == "--xesPath="* ]]; then
		xesPath=$(echo $var | cut -f2 -d=)
	fi

	#redirects data input, for automated testing; stored artifacts are also sent to this dir
	if [[ $var == "--dataDir="* ]]; then
		dataDir=$(echo $var | cut -f2 -d=)
		logPath="$dataDir/testTraces.log"
		syntheticModelPath="$dataDir/model.txt"
		syntheticGraphmlPath="$dataDir/syntheticModel.graphml"
		pnmlPath="$dataDir/testModel.pnml"
		minedGraphmlPath="$dataDir/minedModel.graphml"
		markovModelPath="$dataDir/markovModel.py"
		subdueLogPath="$dataDir/test.g"
		traceGraphPath="$dataDir/traceGraphs.py"
		compressedLog="$dataDir/compressed.g"
		gbadFsmLogPath="$dataDir/test_fsm.g"
	fi
done

if [ "$var" = "empty" ]; then
	echo No xesPath passed. Exiting
	exit
fi

#mine the process model given by the log
##############################################################################
##Prep the java script to be passed to the ProM java cli; note the path parameters to the miningWrapper are relative to the ProM directory
cd "../PromTools"
#Note that the literal ifile/ofile params (testTraces.txt and testModel.pnml) are correct; these are the string params to the mining script generator, not actual file params. 
python $miningWrapper -miner=$minerName -ifile=testTraces.xes -ofile=testModel.pnml -classifierString=$classifierString
#Copy everything over to the ProM environment; simpler to run everything from there.
minerScript="$minerName"Miner.js
promMinerPath=../../ProM/"$minerScript"
cp $minerScript $promMinerPath
cp "$xesPath" ../../ProM/testTraces.xes
cp ./miner.sh ../../ProM/miner.sh

###############################################################################
##Run a process miner to get an approximation of the ground-truth model. Runs a miner with the greatest generalization, least precision.
cd "../../ProM"
sh ./miner.sh -f $minerScript
#copy the mined model back to the SyntheticData folder
#return to test script environment
cd "../scripts/Testing"
cp ../../ProM/testModel.pnml $dataDir/testModel.pnml

#Convert the mined pnml model to graphml
python $pnmlConverterPath $pnmlPath $minedGraphmlPath #--show   #dont show for super huge graphs, common for real data

echo "XES PATH $xesPath    LOG PATH $logPath"
python ../ConversionScripts/xes2log.py $xesPath $logPath --activityKey=concept:name


################################################################################
##Generate sub-graphs from the mined graphml model
python $subgraphGeneratorPath --graphml=$minedGraphmlPath --tracePath=$logPath --outputPath=$subdueLogPath --traceGraphs=$traceGraphPath --gbad
###Added step: gbad-fsm requires a undirected edges declarations, so take the subueLog and just convert the 'd ' edge declarations to 'u '
###python ../ConversionScripts/SubdueLogToGbadFsm.py $subdueLogPath $gbadFsmLogPath

##############################################################################
#Call gbad on the generated traces (note: gbad-prob->insertions, gbad-mdl->modifications/substitutions, gbad-mps->deletions)
#GBAD-FSM: mps param: closer the value to 0.0, the less change one is willing to accept as anomalous. mst: minimum support thresh, best structure must be included in at least *mst* XP transactions
##mdlResult="../TestResults/mdlResult.txt"
##mpsResult="../TestResults/mpsResult.txt"
##probResult="../TestResults/probResult.txt"
##fsmResult="../TestResults/fsmResult.txt"
###fsmTemp="../TestResults/fsmPostProced.txt"
##gbadResult="../TestResults/gbadResult.txt"
##anomalyFile="../TestResults/anomalyResult.txt"

mdlResult="$dataDir/mdlResult.txt"
mpsResult="$dataDir/mpsResult.txt"
probResult="$dataDir/probResult.txt"
fsmResult="$dataDir/fsmResult.txt"
#fsmTemp="../TestResults/fsmPostProced.txt"
gbadResult="$dataDir/gbadResult.txt"
anomalyFile="$dataDir/anomalyResult.txt"


#clear any previous results
cat /dev/null > $mdlResult
cat /dev/null > $mpsResult
cat /dev/null > $probResult
cat /dev/null > $fsmResult

cat /dev/null > dendrogram.txt

gbadThreshold="0.1" #the best performance always seems to be about 0.3; I need to justify this
numTraces="200"
limit="100"   #The default value is computed based on the input graph as |Edges| / 2. 

echo Running gbad-mdl from $gbadMdlPath
#numerical params: for both mdl and mps, 0.2 to 0.5 have worked well, at least for a log with 9/200 anomalous rates. Values of 0.4 or greater risk extemely long running times.
$gbadMdlPath -limit $limit -mdl $gbadThreshold $subdueLogPath > $mdlResult
#echo Running gbad-mps from $gbadMdlPath
#$gbadMdlPath -limit $limit -mps $gbadThreshold $subdueLogPath > $mpsResult
#echo Running gbad-prob from $gbadMdlPath
#$gbadMdlPath -prob 2 $subdueLogPath > $probResult

#run recursive-compression gbad
if [ $recursiveIterations -gt 0 ]; then
	cp $mdlResult lastMdlResult.txt
	#compress the best substructure and re-run; all gbad versions should output the same best-substructure, so using mdlResult.txt's ought to be fine
	python $logCompressor $subdueLogPath lastMdlResult.txt $compressedLog name=SUB_init --deleteSubs=$deleteSubstructures #--showSub
	i="0"
	#test for completion; this is kludgy, but completion is detected when the compressedLog is empty or iterations exhausted.
	#BEWARE of exiting before compression is completed
	while [[ $i -lt $recursiveIterations && -s $compressedLog ]] ; do
		echo Compression iteration $i
#compress the best substructure and re-run; all gbad versions should output the same best-substructure, so using mdlResult.txt's ought to be fine
#python $logCompressor $subdueLogPath lastMdlResult.txt $compressedLog name=SUB$i --deleteSubs=$deleteSubstructures --showSub
		#compressor writes the number of best-substructure instances to ./subsCount.txt file, relative to the compressor's environment
		#Read the subsCount.txt parameter and use it to modify the gbad threshold
		#gbadThreshold=$(cat gbadThresh.txt)
		echo Re-running gbad with threshold $gbadThreshold
		#echo Running gbad-mdl from $gbadMdlPath
		#$gbadMdlPath -mdl $gbadThreshold $compressedLog
		$gbadMdlPath -limit $limit -mdl $gbadThreshold $compressedLog > lastMdlResult.txt
#cat lastMdlResult.txt >> $mdlResult
#echo Running gbad-mps from $gbadMdlPath
#$gbadMdlPath -limit $limit -mps $gbadThreshold $compressedLog >> $mpsResult
		#echo Running gbad-prob from $gbadMdlPath
		#$gbadMdlPath -prob 2 $compressedLog >> $probResult
		#recompress the best substructure and re-run, using the previous compressed log as input and then outputting to it as well
		python $logCompressor $compressedLog lastMdlResult.txt $compressedLog name=SUB$i --deleteSubs=$deleteSubstructures #--showSub
		#increment
		i=$[$i+1]
	done
fi

##run recursive-compression gbad
#if [ $recursiveIterations -gt 0 ]; then
#	cp $mdlResult lastMdlResult.txt
#	for i in $(seq 0 $recursiveIterations); do
#		echo Compression iteration $i
#		#compress the best substructure and re-run; all gbad versions should output the same best-substructure, so using mdlResult.txt's ought to be fine
#		python $logCompressor $subdueLogPath lastMdlResult.txt $compressedLog name=SUB$i --deleteSubs=$deleteSubstructures --showSub
#		echo RUNNING GBAD
#		echo Running gbad-mdl from $gbadMdlPath
#		$gbadMdlPath -mdl $gbadThreshold $compressedLog
#		#$gbadMdlPath -mdl $gbadThreshold $compressedLog > lastMdlResult.txt
#		#cat lastMdlResult.txt >> $mdlResult
#		#echo Running gbad-mps from $gbadMdlPath
#		#$gbadMdlPath -mps $gbadThreshold $compressedLog >> $mpsResult
#		#echo Running gbad-prob from $gbadMdlPath
#		#$gbadMdlPath -prob 2 $compressedLog >> $probResult
#	done
#fi


##Run the frequent subgraph miner
#echo Running gbad-fsm...
#$gbadFsmPath -prob 3 -mst 1 -graph $gbadFsmLogPath #-nameAnomSub  $fsmResult > ./gbadProbOutput.txt
#fsm results have to be post-processed a bit
#grep "transaction containing anomalous structure" $fsmResult | uniq | sort #> $fsmTemp

##Concat the gbad results into a single file so they are easier to analyze at once
cat $mdlResult >    $gbadResult
cat $mpsResult >> $gbadResult
cat $probResult >> $gbadResult

#TODO: The dendrogram.txt is about the last file hardcoded within any scripts, such that it exists only in ./. This could be changed if needed; this call is just a bandaid.
cp dendrogram.txt $dataDir/dendrogram.txt

#could loop here, for different parameters, like bayesThreshold
python ./AnomalyReporter.py -gbadResult=$gbadResult -logFile=$logPath -resultFile=$anomalyFile --dendrogram=$dataDir/dendrogram.txt --dendrogramThreshold=0.18 -markovPath=$markovModelPath -traceGraphs=$traceGraphPath

#dont delete this: copy-paste this to re-run anomaly detection manually from cmd line
#python ./AnomalyReporter.py -gbadResult=../TestResults/gbadResult.txt -logFile=../SyntheticData/testTraces.log -resultFile=../TestResults/anomalyResult.txt --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=../SyntheticData/markovModel.py -traceGraphs=../SyntheticData/traceGraphs.py
#python ./AnomalyReporter.py -gbadResult=../Datasets/Sep21/T1/gbadResult.txt -logFile=../Datasets/Sep21/T1/testTraces.log -resultFile=../Datasets/Sep21/T1/anomalyResult.txt --dendrogram=../Datasets/Sep21/T1/dendrogram.txt --dendrogramThreshold=0.18 -markovPath=../Datasets/Sep21/T1/markovModel.py -traceGraphs=../Datasets/Sep21/T1/traceGraphs.py
