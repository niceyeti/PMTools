
"""
Executes a single run of the Sampling algorithm from Bezerra, outputting results to ./sampleTest/ within the test log directory
parameter given by --indir, using a bunch of processes.

Runtime context: This directory (/Datasets/). The SampleAlgoUtilities path is hardcoded to here.

Input: A directory path to the folder containing the source testTraces.log file
Output: ./sampleTest/ a directory with the runtime artifacts of the test, and the result file, results.txt

Test: 

"""

from __future__ import print_function
import sys
import subprocess
import os
import traceback
import igraph

#fix these
#from SampleAlgoUtilities.SynData2Xes import ToXes
import SampleAlgoUtilities.SynData2Xes


def usage():
	print("Usage: python SampleAlgoTest.py --indir=[folder path to source testTraces.log file]")
	print("Output will be stored in ./sampleTest/ directory")

class SampleAlgoRunner(object):

	def __init__(self):
		self._inputDir = ""
		self._runtimeFolder = ""

	#Returns a .log process log as a list of threeples, (isAnomalous "+"/"-", traceNumber, traceString)	
	def _getLog(self, logPath):
		if not os.path.exists(logPath):
			print("ERROR log path not found in SampleAlgoTest: "+logPath)
			exit()
		
		log = []
		with open(logPath, "r") as logFile:
			for line in logFile.readlines():
				tup = tuple(line.strip().split(","))
				log.append(tup)

		return log

	#@freqThreshold: All traces below @freqThreshold will be returned, as their tuples (+/-,123,asdfdsce)
	#Returns: set of trace-strings below @freqThreshold
	def _getLowFrequencyTraceStrings(self, log, freqThreshold=0.02):
		histogram = dict() #trace string -> int frequency
		outliers = set()
		
		for trace in log:
			traceStr = trace[2]
			if traceStr not in histogram.keys():
				histogram[traceStr] = 1
			else:
				histogram[traceStr] += 1
				
		n = float(len(log))
		for trace in log:
			if (float(histogram[trace[2]]) / n) <= 0.02:
				outliers.add( trace[2] )

		return outliers
	"""
	End to end wrapper script for mining a model, copying the resulting .pnml over
	to running directory, and converting it to graphml.
	
	@xesPath: path to temp xes file, relative to /Datasets
	"""
	def _mineProcessModel(self, xesPath, minerName="alpha"):
		xesPath = xesPath.replace("\\\\","\\").replace("\\","/")
		xesPath = "../Datasets/"+xesPath
	
		#subprocess.execute("sh SampleAlgoArtifacts/mine.sh "+xesPath+" "+minerName)
		print("XES PATH: "+xesPath)
		script = """sh -c  "cd ../PromTools
		pnmlFname=testModel.pnml
		pnmlPath=SampleAlgoUtilities/$pnmlFname
		pnmlConverterPath=../ConversionScripts/Pnml2Graphml.py
		minedGraphmlPath=SampleAlgoUtilities/minedModel.graphml
		xesPath="""+xesPath+"""
		
		#Note that the literal ifile/ofile params (testTraces.txt and testModel.pnml) are correct; these are the string params to the mining script generator, not actual file params. 
		python miningWrapper.py -miner=alpha -ifile=testTraces.xes -ofile=testModel.pnml -classifierString=Activity
		#Copy everything over to the ProM environment; simpler to run everything from there.
		minerScript="""+minerName+"""Miner.js
		promMinerPath=../../ProM/$minerScript
		cp $minerScript $promMinerPath
		cp $xesPath ../../ProM/testTraces.xes
		cp ./miner.sh ../../ProM/miner.sh

		###############################################################################
		##Run a process miner to get an approximation of the ground-truth model. Runs a miner with the greatest generalization, least precision.
		cd ../../ProM
		sh ./miner.sh -f $minerScript
		#copy the mined model back to the SyntheticData folder
		#return to test script environment
		cd ../scripts/Datasets
		cp ../../ProM/testModel.pnml $pnmlPath

		#Convert the mined pnml model to graphml
		python $pnmlConverterPath $pnmlPath $minedGraphmlPath --show
		echo DONE"
		"""

		subprocess.call(script)
		
		graphmlProcessModel = igraph.Graph.Read("SampleAlgoUtilities/minedModel.graphml")
		
		return graphmlProcessModel


	def _outputTempLog(self, log, logPath):
		with open(logPath,"w+") as logFile:
			for trace in log:
				logFile.write(",".join(trace)+"\n")

	#establishes runtime context
	def _initialize(self, indir):
		initializationSucceeded = True
		if indir[-1] != os.sep:
			indir = indir + os.sep
		self._inputDir = indir
		self._runtimeFolder = self._inputDir+"sampleAlgoTest"+os.sep
		#make the running artifacts directory
		if not os.path.exists(self._runtimeFolder):
			os.mkdir(self._runtimeFolder)
		
		self._sourceLogPath = self._inputDir+"testTraces.log"
		if not os.path.exists(self._sourceLogPath):
			print("ERROR test log file not found at: "+self._sourceLogPath)
			initializationSucceeded = False

		self._modelGraphmlPath = "SampleAlgoUtilities/minedModel.graphml"
			
		return initializationSucceeded

	def RunSampleTest(self, indir):
		if self._initialize(indir):
			tempLogPath = self._runtimeFolder+"temp.log"
			tempXesPath = self._runtimeFolder+"temp.xes"
			
			log = self._getLog(self._sourceLogPath)
			#get the low frequency traces; < 0.02 by Bezerra's work on anomaly detection
			lowFrequencyTraceStrings = self._getLowFrequencyTraceStrings(log)
			anomalousTraces = []
			
			print("Testing "+str(len(lowFrequencyTraceStrings))+" low frequency traces: "+str(lowFrequencyTraceStrings))
			
			for trace in lowFrequencyTraceStrings:
				#remove this trace from the log
				reducedLog = self._getFilteredLog(log, trace)
				#output the new log
				self._outputTempLog(reducedLog, tempLogPath)
				#convert temp log 
				self._convertLogToXes(tempLogPath, tempXesPath)
				#mine the model
				graphmlModel = self._mineProcessModel(tempXesPath, minerName="inductive")
				if not self._isReplayableTrace(trace, graphmlModel):
					print("Trace not replayable, flagging as anomalous: "+trace)
					anomalousTraces.append(trace)

			self._recordResults(log, anomalousTraces)
		
		
	#Ripped the definition from the traceReplayer
	"""
	Given a partially-ordered sequence and a graph (process model) on which to replay the sequence, we replay them to derive
	the ground-truth edge transitions (the real ordering) according the given process model. Returns the walk represented by @sequence
	according to the graph.

	@sequence: a sequence of characters representing single activities, partially-ordered
	@graph: the igraph on which to 'replay' the partial-ordered sequence, thereby generating the ordered sequence to return
	"""
	def _isReplayableTrace(self, traceStr, model):
		modelActivities = set([v["name"] for v in model.vs])
		traceActivities = set([c for c in traceStr]+["START","END"]) #START and END are added because they are placeholders in the model, but not in .log files
		
		#A trivial case: verify all trace activities are in model's activities. (The reverse need not be verified: a trace consists of a subset of the model, so all model activities need not be included in trace)
		for traceActivity in traceActivities:
			if traceActivity not in modelActivities:
				print("Trace activity "+traceActivity+" not found in modelActivities, trace flagged as anomalous: "+traceStr)
				return False

		initialEdge = self._getEdge(model, "START", traceStr[0])
		#Another trivial case: if no edge from START to first activity, trace is not replayable
		if initialEdge == None:
			print("No edge found from START to trace beginning, flagged as anomalous: "+traceStr)
			return False

		#The actual search procedure
		if not self._isModelConsistentTrace(traceStr, traceActivities, model):
			return False

		return True
		
	def _getEdge(self, model, srcName, dstName):
		for edge in model.es:
			if model.vs[edge.source]["name"] == srcName and model.vs[edge.target]["name"] == dstName:
				return edge
		return None
		
	def _getVertex(self, activity, model):
		for v in model.vs:
			if v["name"] == activity:
				return v
		#This MUST be unreachable; _getVertex must always be called in a context when it can return a value
		print("ERROR activity "+activity+" not found in model!")
		return None
	
	"""
	The search proc for detecting if a partially-ordered trace string is consistent with a model,
	returning true if traceStr is a valid walk on the model, false otherwise. This is complicated
	by the fact that trace strings are partially ordered, hence you cant just consume their symbols
	sequentially and walk a graph from START to END.
	
	This is a proof-based method. First, mark first activity from START to traceStr[0] (first activity)
	as reachable, iff there is such an edge. Get its out-neighbors, and mark them as "reachable".
	Repeat for all nodes in traceStr sequentially. If any vertex is read from @traceStr and has not
	been marked "reachable", then the trace is not consistent with @model, eg, is not replayable.

	Note that there is a flaw in this algorithm, in that reachability is defined without respect to when the event
	occurred. That is, nodes are simply marked "reachable", and remain so indefinitely. For instance, imagine a model
	with temporal constraints such as only allowing k traversals of a loop; this algorithm would be insensitive
	to the timing of such walks. The assumpton of this project's test data is that we do not have such
	constraints, and that non-replayability can be sufficiently detected via structural inconsistencies.
	"""
	def _isModelConsistentTrace(self, traceStr, traceActivities, model):
		model.vs["isReachable"] = False #mark all vertices as unreachable, initially
	
		startEdge = self._getEdge(model, "START", traceStr[0])
		if startEdge is None:  #already checked in the main _isReplayableTrace function, but still a responsibility of this function too
			print("No edge from START to "+traceStr[0]+". Trace flagged as non-model consistent: "+traceStr)
			return False

		#mark initial node as reachable to begin replay search
		model.vs[startEdge.target]["isReachable"] = True
			
		for i in range(len(traceStr)):
			activity = traceStr[i]
			if not self._isReachableActivity(activity, traceActivities, model):
				return False

		return True

	#Returns neighbors reachable from @activity ia its outgoing edges
	def _getOutneighbors(self, activity, model):
		#gets the neighbors by name
		neighborNames = model.neighbors(activity, mode="out")
		outNeighbors = [vertex for vertex in model.vs if vertex["name"] in neighborNames]
		return outNeighbors

	"""
	Recursively-defined utility for _isModelConsistentTrace. Note that out-neighbors are
	only marked as reachable if they are in the traceActivitySet, an important but subtle potential mistake if not checked.
	"""
	def _isReachableActivity(self, activity, traceActivitySet, model):
		#if activity was not marked "reachable" via a previous activity (including START), return False
		if self._getVertex(activity, model)["isReachable"] == False:
				return False
		#get all out neighbors: all activities to which this activity may traverse in one time step
		outNeighbors = self._getOutneighbors(activity, model)
		#mark all out-neighbors "reachable" that are also in traceActivity set
		for neighbor in outNeighbors:
			if neighbor["name"] in traceActivitySet:
				neighbor["isReachable"] = True
		#if "reachable" neighbors >= 1, proceed. If == 0, return False (no downstream activities from this vertex)
		numReachable = sum([1 for neighbor in outNeighbors if neighbor["isReachable"]])
		if len(outNeighbors) == 0 or numReachable == 0:
			return False

		return True
		
	def _convertLogToXes(self, logPath="temp.log", xesPath="temp.xes"):
		#call the converter
		SampleAlgoUtilities.SynData2Xes.ToXes(logPath,xesPath)

	"""
	Given a log in the form of threeples (+/-,123, advbdsf), this removes all threeples matching @traceStr.
	"""
	def _getFilteredLog(self, log, traceStr):
		filteredLog = []
		
		for trace in log:
			if trace[2] != traceStr:
				filteredLog.append(trace)
		
		return filteredLog

	def _getTracesFromTraceString(self, log, traceString):
		traces = []
		
		for traceTuple in log:
			if traceTuple[2].strip() == traceString.strip():
				traces.append(traceTuple)

		#All traceStrings must match some original trace/traces in the log, since that's where they came from
		if len(traces) == 0:
			print("ERROR no original traces mapped by traceString: "+traceString)
				
		return traces

	"""
	Just the list-of-trace-string version of the above
	"""
	def _getTracesFromTraceStrings(self, log, traceStrings):
		traces = []
		for traceString in traceStrings:
			traces += self._getTracesFromTraceString(log, traceString)

		return traces
		
	"""
	@log: The log, as a list of string threeples ("+"/"-", traceId, traceStr)
	@anomalousTraceStrings: The trace strings marked as anomalous
	"""
	def _recordResults(self, log, anomalousTraceStrings):
		
		falsePositives = 0
		falseNegatives = 0
		truePositives = 0
		trueNegatives = 0
		
		totalPositives = sum([1 for trace in log if "+" in trace[0]])
		n = len(log)
		totalNegatives = sum([1 for trace in log if "-" in trace[0]])
		if (totalPositives + totalNegatives) != n:
			print("ERROR totalPositives="+str(totalPositives)+" totalNegatives="+str(totalNegatives)+" sum != n: "+str(n))
		
		print("Log contains "+str(totalPositives)+" of "+str(n)+" traces")
		
		#get all original trace tuples from the anomalous trace strings 
		anomalousTraces = self._getTracesFromTraceStrings(log, anomalousTraceStrings)
		print("GOT "+str(len(anomalousTraces))+" ORIGINAL TRACES FROM "+str(len(anomalousTraceStrings))+" ANOMALOUS TRACE STRINGS")
		for trace in anomalousTraces:
			print(str(trace))
			if "+" in trace[0]:
				truePositives += 1
			if "-" in trace[0]:
				falsePositives += 1
		
		falseNegatives = totalPositives - truePositives  #trueAnomalies.difference(reportedAnomalyIds)
		#cheating: true negatives can be derived from the three values above TN = N - FP - FN - TP
		trueNegatives = n - falseNegatives - falsePositives  - truePositives
		if (trueNegatives + falseNegatives + falsePositives + truePositives) != n:
			print("ERROR TN, FP, etc do not sum to n properly!")
		
		#calculate recall, preision, etc
		errorRate = float(falseNegatives + falsePositives) / float(n) #error rate = (FP + FN) / N = 1 - accuracy
		accuracy =  float(trueNegatives + truePositives) / float(n) # accuracy = (TN + TP) / N = 1 - error rate

		#calculate precision: TP / (FP + TP)
		denom = float(falsePositives + truePositives)
		if denom > 0.0:
			precision =  float(truePositives) / denom
		else:
			print("WARNING: precision denominator is zero in AnomalyReporter.py")
			precision = 0.0
		#exception case: If there are no anomalies in the data, and the algorithm doesn't score any false positives, then precision and recall are zero by their
		#normal definition, but logically they are 1.0.
			
		#false positive rate; needed for doing roc curves
		#denom = float(len(falsePositives) + len(trueNegatives))
		#if denom > 0:
		#	fpr = float(len(falsePositives)) / denom
		#else:
		#	fpr = 0.0
		
		#calculate recall: TP / (TP + FN)
		denom = float(truePositives + falseNegatives)
		if denom > 0.0:
			recall = float(truePositives) / denom
		else:
			print("WARNING: recall denominator is zero in AnomalyReporter.py")
			recall = 0.0

		#f -measure
		denom = precision + recall
		if denom > 0.0:
			fMeasure = (precision * recall * 2) / denom
		else:
			fMeasure = 0.0
		
		with open("sampleResult.txt", "w+") as ofile:
			#trueAnomalies = sorted(list(trueAnomalies))
			ofile.write("truePositives:"+str(truePositives)+"\n")
			ofile.write("trueNegatives:"+str(trueNegatives)+"\n")
			ofile.write("falsePositives:"+str(falsePositives)+"\n")
			ofile.write("falseNegatives:"+str(falseNegatives)+"\n")
			ofile.write("precision:"+str(precision)+"\n")
			ofile.write("recall:"+str(recall)+"\n")
			ofile.write("error:"+str(errorRate)+"\n")
			ofile.write("accuracy:"+str(accuracy)+"\n")
			#ofile.write("trueAnomalies:"+str(trueAnomalies)+"\n")
			#ofile.write("reportedAnomalyIds:"+str(reportedAnomalyIds).replace("set()","{}")+"\n")
			ofile.write("fMeasure:"+str(fMeasure))

def main():

	if len(sys.argv) < 2:
		usage()
		exit()
	
	indir = ""
	for arg in sys.argv:
		if "--indir=" in arg:
			indir = arg.split("=")[-1]
	if len(indir) == 0:
		usage()
		exit()

	if indir[-1] != os.sep:
		indir = indir + os.sep

	if not os.path.exists(indir+"testTraces.log"):
		print("ERROR no testTraces.log found in ")

	runner = SampleAlgoRunner()
	runner.RunSampleTest(indir)
		
if __name__ == "__main__":
	main()
