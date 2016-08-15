"""
Given the output of gbad containing found-anomalies, and the original trace log containing
+/- anomaly labellings, this object compares the two nd generates the matrix for
true positives, false positives, true negatives, and false negatives.

The info is just printed to the output, but keep it parseable if possible.
"""
from __future__ import print_function
import sys




class AnomalyReporter(object):
	def __init__(self, gbadPath, logPath):
		self._gbadPath = gbadPath
		self._logPath = logPath
		
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
		self._traces = [trace.split(",") for trace in logFile.readlines() if len(trace.strip()) > 0]
		#get the subset of the traces which are anomalies
		self._anomalies = [anom for anom in self._traces if anom[1] == "+"]
		self._numAnomalies = len(self._anomalies)
		
	def Compile():
		gbadFile = open(self._gbadPath, "r")
		logFile = open(self._logPath, "r")

		self._parseGbadAnomalies(gbadFile)
		self._parseLogAnomalies(logFile)

		for anomal
		
	
		
def usage():
	print("Usage: python ./AnomalyReporter.py -gbadResult=[path to gbad output] -logFile=[path to log file containing anomaly labellings]")
		
def main():
	if len(sys.argv) != 3:
		print("ERROR incorrect num args")
		usage()
		exit()

	reporter = AnomalyReport(gbadPath, logPath)
	reporter.CompileResults()
	
if __name__ == "__main__":
	main()



