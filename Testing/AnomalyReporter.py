"""
Given the output of gbad containing found-anomalies, and the original trace log containing
+/- anomaly labellings, this object compares the two nd generates the matrix for
true positives, false positives, true negatives, and false negatives.

The info is just printed to the output, but keep it parseable if possible.
"""
from __future__ import print_function
import sys




class AnomalyReporter(object):
	def __init__(self, gbadPath, logPath, resultPath):
		self._gbadPath = gbadPath
		self._logPath = logPath
		self._resultPath

	"""
	Given a file containing gad output, parses the text for all of the anomalies detected. Each
	anomaly must contain the corresponding trace number associated with a trace in the original
	log file (labelled +/- for anomaly status).
	
	Returns: All of the anomalies listed in the gbad output, formatted as a list of <integer, string-text> pairs, where the
	integer is the key of the trace label (XP label in gbad) and the string text is the raw gbad record for that anomaly (likely unused).
	Returns empty list if no anomalies were found.
	"""
	def _parseGbadAnomalies(self):
		
		
		
	"""
	Parses a log file into the object's internal storage.
	
	@self._anomalies: a list of anomalous traces (tokenized by comma)
	
	"""
	def _parseLogAnomalies(self,logFile):
		#maintain traces internally as a list of <traceNo,+/-,trace> string tuples
		self._logTraces = [trace.split(",") for trace in logFile.readlines() if len(trace.strip()) > 0]
		#get the subset of the traces which are anomalies
		self._logAnomalies = [anom for anom in self._traces if anom[1] == "+"]
		#get the non-anomalies
		self._logNegatives = [anom for anom in self._traces if anom[1] == "-"]
		
	"""
	Keep this clean and easy to parse.
	"""
	def _outputResults(self):
		ofile = open(self._resultPath, "w+")
		ofile.write("Statistics for log parsed from "+self._logPath+", anomalies detected")
		ofile.write("True positives:\t"+str(len(self._truePositives))+"\t"+str(self._truePositives))
		ofile.write("False positives:\t"+str(len(self._falsePositivies))+"\t"+str(self._falsePositivies))
		ofile.write("True negatives:\t"+str(len(self._trueNegatives))+"\t"+str(self._trueNegatives))
		ofile.write("False negatives:\t"+str(len(self._falseNegatives))+"\t"+str(self._falseNegatives))
		ofile.close()
		
	"""
	Opens traces and gbad output, parses the anomalies and other data from them, necessary
	to compute false/true positives/negatives and then output them.
	"""
	def Compile():
		gbadFile = open(self._gbadPath, "r")
		logFile = open(self._logPath, "r")

		self._parseGbadAnomalies(gbadFile)
		self._parseLogAnomalies(logFile)

		#create the true anomaly and detected anomaly sets via the trace-id's
		truePositiveSet = set( [int(anomaly[0] for anomaly in self._logAnomalies)] )
		trueNegativeSet = set( [int(anomaly[0] for anomaly in self._logNegatives)] )
		detectedAnomalies = set( [detectedAnomaly[0] for detectedAnomaly in self._detectedAnomalies] )

		#store overall stats and counts
		self._numTraces = len(self._logTraces)
		self._numTrueAnomalies = len(self._logAnomalies)
		self._numDetectedAnomalies = len(self._detectedAnomalies)

		#get the false/true positives/negatives using set arithmetic
		self._truePositives = detectedAnomalies & truePositiveSet
		self._falsePositives = detectedAnomalies - truePositiveSet
		self._trueNegatives = trueNegativeSet - detectedAnomalies
		self._falseNegatives = truePositiveSet - detectedAnomalies

		self._outputResults()
		
		print("Result Reporter completed.")
		
def usage():
	print("Usage: python ./AnomalyReporter.py -gbadResult=[path to gbad output] -logFile=[path to log file containing anomaly labellings] -resultFile=[result output path]")
		
def main():
	if len(sys.argv) != 4:
		print("ERROR incorrect num args")
		usage()
		exit()
		
	gbadPath = sys.argv[1].split("=")[1]
	logPath = sys.argv[2].split("=")[1]
	resultPath = sys.argv[3].split("=")[1]
	
	reporter = AnomalyReport(gbadPath, logPath, resultPath)
	reporter.CompileResults()

if __name__ == "__main__":
	main()



