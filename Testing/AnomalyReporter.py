"""
Given the output of gbad containing found-anomalies, and the original trace log containing
+/- anomaly labelings, this object compares the two and generates the matrix for
true positives, false positives, true negatives, and false negatives.

The gbad output may contain output of any gbad version (mdl, mps, prob), and output of each gbad
version can be concatenated into a single file as input to this script. Mdl and mps output is the same,
but the fsm version declares anomalies slightly differently. All are plaintext files, which ought to be
updated to something more rigorous. This doesn't handle fsm output directly, but can with a little
preprocessing: grep "transaction containing anomalous structure" $fsmResult | uniq | sort > $fsmTemp

The info is just printed to the output, but keep it parseable if possible.
"""
from __future__ import print_function
import sys

class AnomalyReporter(object):
	def __init__(self, gbadPath, logPath, resultPath):
		self._gbadPath = gbadPath
		self._logPath = logPath
		self._resultPath = resultPath

	"""
	Given a file containing gad output, parses the text for all of the anomalies detected. Each
	anomaly must contain the corresponding trace number associated with a trace in the original
	log file (labelled +/- for anomaly status).
	
	Returns: A list of integers that are the ids of any 
	"""
	def _parseGbadAnomalies(self, gbadFile):
		self._detectedAnomalyIds = []
		gbadOutput = gbadFile.readlines()
		#print("output: "+gbadOutput)
		gbadFile.close()

		"""
		Gbad output (in the versions I've used) always has anomalies anchored with the file-unique string
		"from example xx" where xx is the integer number of the anomalous graph, the same as the trace id in the trace log.
		Thus, search for all lines with this string, parse the number, and we've a list of trace-ids for the anomalies.
		"""
		for line in gbadOutput:
			#detects gbad-mdl, -mps, -prob anomal declarations (mdl/mps use "from example", gbad-prob uses "from positive example")
			if "from example " in line:
					#print("found anom: "+line)
					#parses 50 from 'from example 50:'
					id = int(line.strip().split("from example ")[1].replace(":",""))
					self._detectedAnomalyIds.append(id)
			#detects gbad-prob anomalous subgraph example declarations
			if "in original example " in line:
					#print("found anom: "+line)
					#parses 50 from 'in original example 50)'
					id = int(line.strip().split("in original example ")[1].replace(")",""))
					self._detectedAnomalyIds.append(id)

			#detects output format of gbad-fsm
			if "transaction containing anomalous structure:" in line:
				id = int(line.split("structure:")[1].strip())
				self._detectedAnomalyIds.append(id)
				
	"""
	Parses a trace log file into the object's internal storage. These are the ground truth anomalies, not those detected by gbad.
	
	@self._anomalies: a list of anomalous traces (tokenized by comma)
	"""
	def _parseLogAnomalies(self,logFile):
		#maintain traces internally as a list of <traceNo,+/-,trace> string 3-ples
		self._logTraces = [trace.split(",") for trace in logFile.readlines() if len(trace.strip()) > 0]
		#get the subset of the traces which are anomalies
		self._logAnomalies = [trace for trace in self._logTraces if trace[1] == "+"]
		#get the non-anomalies
		self._logNegatives = [trace for trace in self._logTraces if trace[1] == "-"]
		logFile.close()
		
	"""
	Given a float in range 0.0 to 1.0, such as 0.4567532, returns "45.67%" (hundredths precision)
	"""
	def _floatToPctStr(self, f):
		return str(float(int(f * 10000)) / 100.0)+"%"

	"""
	Keep this clean and easy to parse.
	"""
	def _outputResults(self):	
		output = "Statistics for log parsed from "+self._logPath+", anomalies detected\n"
		#output += "True positives:  \t"+str(len(self._truePositives))+"\t"+str(self._truePositives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "False positives:  \t"+str(len(self._falsePositives))+"\t"+str(self._falsePositives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "True negatives: \t"+str(len(self._trueNegatives))+"\t"+str(self._trueNegatives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "False negatives: \t"+str(len(self._falseNegatives))+"\t"+str(self._falseNegatives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"

		output += ("Num traces (N): \t"+str(self._numTraces)+"\n")
		output += ("Accuracy:          \t"+str(self._accuracy)+"  ("+self._floatToPctStr(self._accuracy)+")\n")
		output += ("Error rate:         \t"+str(self._errorRate)+"  ("+self._floatToPctStr(self._errorRate)+")\n")
		output += ("Recall:              \t"+str(self._recall)+"  ("+self._floatToPctStr(self._recall)+")\n")
		output += ("Precision:          \t"+str(self._precision)+"  ("+self._floatToPctStr(self._precision)+")\n")
		
		output += ("True positives:   \t"+str(len(self._truePositives))+"\t"+str(self._truePositives)+"\n")
		output += ("False positives:  \t"+str(len(self._falsePositives))+"\t"+str(self._falsePositives)+"\n") 
		output += ("True negatives: \t"+str(len(self._trueNegatives))+"\t"+str(self._trueNegatives)+"\n")
		output += ("False negatives: \t"+str(len(self._falseNegatives))+"\t"+str(self._falseNegatives)+"\n")

		print(output)
		
		ofile = open(self._resultPath, "w+")
		ofile.write(output)
		ofile.close()

	"""
	Gbad doesn't always report all instances of a given anomaly; so if "ABC" is reported as an 
	anomaly, it doesn't always report all "ABC" traces as anomalies in it results. 
	
	NOTE: I've only currently written this to look for traces (strings) in the trace file which are
	matching strings. This covers 99% of the cases, however, traces like "ACB" could theoretically
	be included and NOT caught as equivalent to some found-anomaly "ABC". THIS NEEDS TO BE FIXED.
	That is, for each anomaly, we need to reconstruct it graphically according to the mined model, then compare 
	the anomaly to all other traces as graphs.
	
	@anoms: list of anomalies as a list of 3-ples: string-id (the first field of each trace in logTraces), +/-, and traceStr
	
	returns: Full list of anomalous traces as 3-ples.
	"""
	def _unifyAnomalies(self):
		#print("detected: "+str(set(self._detectedAnomalyIds)))
		#print("traces: "+str(self._logTraces))
		anoms = []
		#get the anomaly list as a list of 3-ples
		for id in set(self._detectedAnomalyIds):
			for trace in self._logTraces:
				if trace[0] == str(id):
					anoms.append(trace)
		
		#print("traces: "+str(anoms))
	
		ids = set([a[0] for a in anoms])
		equivalentAnoms = []
		#given each anomaly, look for others with the same trace-string which are not yet included in the anomaly set
		for anom in anoms:
			id = anom[0]
			traceStr = anom[2]
			#search for other log-traces with this same trace-string. This is an insufficient match, since these are technically graphs.
			for logTrace in self._logTraces:
				#if logTrace[2] == traceStr:
				#	print("traceStr hit"+str(logTrace))#+"  ids: "+str(ids))
				if logTrace[2] == traceStr and logTrace[0] not in ids:
					#print("Extra anomaly detected for "+traceStr+" "+id+": "+logTrace[0])
					equivalentAnoms.append(logTrace)
					ids.add(logTrace[0])
		
		anoms += equivalentAnoms
					
		#print("all anoms: "+str(anoms))
		return anoms

	"""
	Opens traces and gbad output, parses the anomalies and other data from them, necessary
	to compute false/true positives/negatives and then output them to file.
	"""
	def CompileResults(self):
		gbadFile = open(self._gbadPath, "r")
		logFile = open(self._logPath, "r")

		self._parseGbadAnomalies(gbadFile)
		self._parseLogAnomalies(logFile)
		#gbad doesn't always report all equivalent anomalies; this simply unifies all reported anomalies with traces that are the same
		self._detectedAnomalyIds = [int(trace[0]) for trace in self._unifyAnomalies()]

		#create the true anomaly and detected anomaly sets via the trace-id numbers
		truePositiveSet = set( [int(anomaly[0]) for anomaly in self._logAnomalies] )
		trueNegativeSet = set( [int(anomaly[0]) for anomaly in self._logNegatives] )
		detectedAnomalies = set(self._detectedAnomalyIds)

		#store overall stats and counts
		self._numDetectedAnomalies = detectedAnomalies
		self._numTraces = len(self._logTraces)
		self._numTrueAnomalies = len(self._logAnomalies)

		#get the false/true positives/negatives using set arithmetic
		self._truePositives = detectedAnomalies & truePositiveSet
		self._falsePositives = detectedAnomalies - truePositiveSet
		self._trueNegatives = trueNegativeSet - detectedAnomalies
		self._falseNegatives = truePositiveSet - detectedAnomalies

		#compile other accuracy stats
		self._errorRate = float(len(self._falseNegatives) + len(self._falsePositives)) / float(self._numTraces) #error rate = (FP + FN) / N = 1 - accuracy
		self._accuracy =  float(len(self._trueNegatives) + len(self._truePositives)) / float(self._numTraces) # accuracy = (TN + TP) / N = 1 - error rate

		#calculate precision: TP / (FP + TP)
		denom = float(len(self._falsePositives) + len(self._truePositives))
		if denom > 0.0:
			self._precision =  float(len(self._truePositives)) / denom
		else:
			self._precision = 0.0
		
		#calculate recall: TP / (TP + FN)
		denom = float(len(self._truePositives) + len(self._falseNegatives))
		if denom > 0.0:
			self._recall = float(len(self._truePositives)) / denom
		else:
			self._recall = 0.0
		
		#convert all sets to sorted lists
		self._truePositives = sorted(list(self._truePositives))
		self._falsePositives = sorted(list(self._falsePositives))
		self._trueNegatives = sorted(list(self._trueNegatives))
		self._falseNegatives = sorted(list(self._falseNegatives))

		self._outputResults()
		
		print("Result Reporter completed.")
		
def usage():
	print("Usage: python ./AnomalyReporter.py -gbadResultFiles=[path to gbad output] -logFile=[path to log file containing anomaly labellings] -resultFile=[result output path]")
	print("To get this class to evaluate multiple gbad result files at once, just cat the files into a single file and pass that file.")

def main():
	if len(sys.argv) != 4:
		print("ERROR incorrect num args")
		usage()
		exit()

	gbadPath = sys.argv[1].split("=")[1]
	logPath = sys.argv[2].split("=")[1]
	resultPath = sys.argv[3].split("=")[1]
	
	reporter = AnomalyReporter(gbadPath, logPath, resultPath)
	reporter.CompileResults()

if __name__ == "__main__":
	main()



