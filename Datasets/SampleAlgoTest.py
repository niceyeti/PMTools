
"""
Executes a single run of the Sampling algorithm from Bezerra, outputting results to ./sampleTest/ within the test log directory,
using a bunch of processes.

Input: A directory path to the folder containing the source testTraces.log file
Output: ./sampleTest/ a directory with the runtime artifacts of the test, and the result file, results.txt


"""

from __future__ import print_function
import sys
import subprocess
import os
import traceback
import igraph

#fix these
import SynData2Xes


def usage():
	print("Usage: python SampleAlgoTest.py --indir=[folder path to source testTraces.log file]")
	print("Output will be stored in ./sampleTest/ directory")

class SampleAlgoRunner(object):

	def __init__(self):
		pass

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
		
	#End to end wrapper script for mining a model, copying the resulting .pnml over to running directory, and converting it to graphml
	def _mineProcessModel(self, xesPath, minerName="alpha"):
	
		subprocess.execute("sh SampleAlgoArtifacts/mine.sh "+xesPath+" "+minerName)
		script = """sh -c  "cd ../PromTools
		pnmlPath=testModel.pnml
		pnmlConverterPath=../ConversionScripts/Pnml2Graphml.py
		minedGraphmlPath=minedModel.graphml
		
		#Note that the literal ifile/ofile params (testTraces.txt and testModel.pnml) are correct; these are the string params to the mining script generator, not actual file params. 
		python miningWrapper.py -miner=alpha -ifile=testTraces.xes -ofile=testModel.pnml -classifierString=Activity
		#Copy everything over to the ProM environment; simpler to run everything from there.
		minerScript=alphaMiner.js
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
		cp ../../ProM/testModel.pnml SampleAlgoArtifacts/testModel.pnml

		#Convert the mined pnml model to graphml
		python $pnmlConverterPath $pnmlPath $minedGraphmlPath --show
		echo DONE"
		"""

		subprocess.call(script)
		
		graphmlProcessModel = igraph.Graph.Read("SampleAlgoArtifacts/minedModel.graphml")
		
		return graphmlProcessModel


	def _outputTempLog(self, log):
		with open("temp.log","w+") as logFile:
			for trace in log:
				logFile.write(",".join(trace)+"\n")
		
	def RunSampleTest(self, indir, xesConverterPath="../.."):
		
		xesConverterPath = 



		self._makeTestDir(indir)
		
		if indir[-1] != os.sep:
			indir = indir + os.sep
		
		log = self._getLog(indir+"testTraces.log")
		#get the 
		lowFrequencyTraces = self._getLowFrequencyTraces(log)
		
		print("Testing "+str(len(lowFrequencyTraces))+" ")
		for trace in lowFrequencyTraces:
			#remove this trace from the log
			reducedLog = self._getFilteredLog(trace)
			#output the new log
			self._outputTempLog(reducedLog)
			#convert temp log 
			self._convertLogToXes("temp.log")
			#mine the model
			graphmlModel = _mineProcessModel(logPath)
			if not _isReplayableTrace(trace, graphmlModel):
				anomalousTraces.append(trace)
			
		_recordResults(log, anomalousTraces)
		
		
		#algorithm: given the log, extract all traces with frequency < 2%, mine model, replay trace on model; if not replayable, the trace is added to anomaly set
		
	#Ripped the definition from the traceReplayer
	def _isReplayableTrace(self, traceStr, model):
		
		
	def _convertLogToXes(self, logPath="temp.log"):
		#call the converter
		SynData2Xes.ToXes(logPath,"temp.xes")

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
	def _getTracesFromTraceStrings(self, log, traceStrings)
		traces = []
		for traceString in traceStrings:
			traces += _getTracesFromTraceString(log, traceString)

		return traces
		
	"""
	@log: The log, as a list of string threeples ("+"/"-", traceId, traceStr)
	@anomalousTraces: The trace strings marked as anomalous
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
		anomalousTraces = _getTracesFromTraceStrings(anomalousTraceStrings)
		print("GOT "+str(len(anomalousTraces))+" ORIGINAL TRACES")
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


	def makeTestDir(self):
		if not os.path.exists("./sampleTest"):
			os.mkdir("sampleTest")

def main():

	if len(sys.agv) < 2:
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
		indir = indir + o.sep
		
	if not os.path.exists(indir+"testTraces.log"):
		print("ERROR no testTraces.log found in ")

	runner = SampleAlgoRunner()
	runner.RunSampleTest(indir)
		
if __name__ == "__main__":
	main()
