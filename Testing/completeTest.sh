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

logCompressor="./SubdueLogCompressor.py"
pnmlPath="../SyntheticData/testModel.pnml"
pnmlConverterPath="../ConversionScripts/Pnml2Graphml.py"
minedGraphmlPath="../SyntheticData/minedModel.graphml"
markovModelPath="../SyntheticData/markovModel.py"
subgraphGeneratorPath="./GenerateTraceSubgraphs.py"
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

#noise rates
noiseRate="0.0"

#get the command line arg switches, if any
generateData="false"
deleteSubstructures="false"
recursiveIterations="0"
for var in "$@"; do
	#detect the data generation bool
	if [ "$var" = "--generate" ]; then
		generateData="true"
	fi
	#get the number of recursive iterations, if any
	if [[ $var == "--recurse="* ]]; then
		recursiveIterations=$(echo $var | cut -f2 -d=)
	fi
	#detect the substructure deletion flag (only meaningful if --recurse is passed as well)
	if [ "$var" = "--deleteSubs" ]; then
		deleteSubstructures="true"
	fi
	#get the number of recursive iterations, if any
	if [[ $var == "--noiseRate="* ]]; then
		noiseRate=$(echo $var | cut -f2 -d=)
	fi
done

#####################DATA GENERATION AND NOISING###################################
#go to DataGenerator folder, and operate there until data fully ready to mine/run/compress
cd "../DataGenerator"

### If generating data, the data generator will generate and store a model, then emit traces from it in a .log file, then convert these to xes.
if [ $generateData = "true" ]; then
	###############################################################################
	##Generate a model containing appr. 20 activities, and generate 1000 traces from it.
	sh ./generate.sh 20 200 $logPath $syntheticGraphmlPath
fi

#add noise to original/synthetic log as requested, before mining the new model
if [ $noiseRate -gt 0 ]; then
	python LogNoiser.py -inputLog=$logPath -outputLog=$noisedLog -noiseRate=$noiseRate
	logPath=$noisedLog
fi

#convert synthetic data to xes format for process mining
python SynData2Xes.py -ifile=$logPath -ofile=$xesPath
##############################################################################


#mine the process model given by the log
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
limit="50"   #The default value is computed based on the input graph as |Edges| / 2. 


echo Running gbad-mdl from $gbadMdlPath
#numerical params: for both mdl and mps, 0.2 to 0.5 have worked well, at least for a log with 9/200 anomalous rates. Values of 0.4 or greater risk extemely long running times.
$gbadMdlPath -limit $limit -mdl $gbadThreshold $subdueLogPath > $mdlResult
echo Running gbad-mps from $gbadMdlPath
$gbadMdlPath -limit $limit -mps $gbadThreshold $subdueLogPath > $mpsResult
#echo Running gbad-prob from $gbadMdlPath
#$gbadMdlPath -prob 2 $subdueLogPath > $probResult

#run recursive-compression gbad
if [ $recursiveIterations -gt 0 ]; then
	cp $mdlResult lastMdlResult.txt
	#compress the best substructure and re-run; all gbad versions should output the same best-substructure, so using mdlResult.txt's ought to be fine
	python $logCompressor $subdueLogPath lastMdlResult.txt $compressedLog name=SUB_init --deleteSubs=$deleteSubstructures --showSub
	for i in $(seq 0 $recursiveIterations); do
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
		cat lastMdlResult.txt >> $mdlResult
		echo Running gbad-mps from $gbadMdlPath
		$gbadMdlPath -limit $limit -mps $gbadThreshold $compressedLog >> $mpsResult
		#echo Running gbad-prob from $gbadMdlPath
		#$gbadMdlPath -prob 2 $compressedLog >> $probResult
		#recompress the best substructure and re-run, using the previous compressed log as input and then outputting to it as well
		python $logCompressor $compressedLog lastMdlResult.txt $compressedLog name=SUB$i --deleteSubs=$deleteSubstructures --showSub
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
cat $mdlResult > $gbadResult
cat $mpsResult >> $gbadResult
cat $probResult >> $gbadResult
#cat $fsmResult >> $gbadResult

#python ./AnomalyReporter.py -gbadResult=$gbadResult -logFile=$logPath -resultFile=$anomalyFile
python ./AnomalyReporter.py -gbadResult=$gbadResult -logFile=$logPath -resultFile=$anomalyFile --dendrogram=dendrogram.txt --dendrogramThreshold=0.18 -markovPath=$markovModelPath



