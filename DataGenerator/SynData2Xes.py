"""
Brief script for converting the output of DataGenerator to xes-format.

The DataGenerator outputs traces in the form [traceno],[isAnomalous],[sequence]:
	1,+,ABCDEFG
	2,-,ABCDEGF
	...

This script converts these into xes traces.
"""

from __future__ import print_function
import sys
import xes
import copy

"""
Just a utility for reading the trace file traces into a list of traces, each of which is a three-tuple
of [traceNo<int>, isAnomaly<bool>, sequence<list of chars>].

Returns: A list of traces. 
"""
def BuildTraces(ipath):
	ifile = open(ipath,"r")
	traces = []

	for line in ifile.readlines():
		if len(line) > 2:
			params = line.strip().split(",")
			if len(params) != 3:
				print("ERROR params != 3 in ToXes(), poorly formatted trace: "+line)
			else:
				#parse the trace
				traceNo = int(params[0])
				hasAnomaly = params[1] == "+"
				#detect bad anomaly flags
				if params[1] not in "+" and params[1] not in "-":
					print("ERROR poorly formatted anomaly flag in ToXes() for line: "+line)
					hasAnomaly = "UNKNOWN"
				sequence = [activity for activity in params[2]]
				#print("Trace number: "+str(traceNo))
				#print(params[1])
				#print(str(sequence))
				#append this trace to the trace list
				traces.append([traceNo,hasAnomaly,sequence])
	ifile.close()
	
	return traces

"""
Converts the trace list output by BuildTraces() into the target format of the xes developer's example.
Each trace is named with its traceNo, and an isAnomalous label. The partially-ordered events only
contain the name of the event, no time-step info.

Returns: An xes.log object defined by the input trace list.
"""
def BuildXesLog(traces):
	log = xes.Log()

	i = 0
	for trace in traces:
		#the name of the trace is just the trace number
		traceName = str(trace[0])
		#add the anomaly status of the trace; this likely won't be used by any ProM or process-discovery tools, but is worth preserving
		isAnomalous = str(trace[1])
		#build the trace info
		t = xes.Trace()
		traceNameAttr = xes.Attribute(type="string", key="concept:name", value=traceName)
		traceIsAnomalousAttr = xes.Attribute(type="string", key="concept:isAnomalous", value=isAnomalous)
		#store both the trace name and the anomaly-status in the trace attributes
		t.attributes = [traceNameAttr, traceIsAnomalousAttr]
		#add the events to the trace; the event sequence is just an ordered sequence of characters with no other info
		for eventName in trace[2]:
			e = xes.Event()
			e.attributes = [
				xes.Attribute(type="string", key="concept:name", value=eventName),
				xes.Attribute(type="string", key="Activity", value=eventName)
				#xes.Attribute(type="string", key="Activity", value=eventName)
			]
			t.add_event(e)
		#add the trace
		log.add_trace(t)
		#print("here: "+str(i)+" of "+str(len(traces)))
		i += 1
		
	#add the classifiers
	log.classifiers = [
		#xes.Classifier(name="org:resource",keys="org:resource"),
		#xes.Classifier(name="concept:name",keys="concept:name")
		#xes.Classifier(name="concept:traceName",keys="concept:traceName"),
		#xes.Classifier(name="concept:isAnomalous",keys="concept:isAnomalous")
		xes.Classifier(name="Activity", keys="Activity"),
		xes.Classifier(name="concept:name",keys="concept:name")
	]

	return log

"""

"""	
def WriteLog(log,opath):
	#write the log
	ofile = open(opath, "w+")
	ofile.write(str(log))
	ofile.close()

"""
Converts a synthetic trace file to xes format.

Trace files are formatted in csv as:
	[traceno],[+/-],[the trace, e.g. ABCDEJGJDN...]
	
Thus the 'trace' is merely a ordered sequence of characters, with each character representing an activity id.
The characters represent semi-ordered activities; 'semi-ordered' in that parallel activities may occur in any order wrt
their concurrent counterparts. These activities become the 'event' items in the Xes log, for which <events> are treated
as ordered within the scope of some trace.
"""
def ToXes(ipath,opath):
	print("Building xes log from synthetic data file "+ipath+". Xes will be written to "+opath)
	traces = BuildTraces(ipath)
	print("Read "+str(len(traces))+" traces from "+ipath)
	log = BuildXesLog(traces)
	print("Log built, writing xes to "+opath)
	WriteLog(log,opath)
	print("Complete.")

def usage():
	print("Usage: python ./SynData2Xes.py -ifile=[path to input file of synthetic data] -ofile=[output path for xes log file]")	

def main():
	if len(sys.argv) < 3:
		print("ERROR insufficient parameters")
		usage()
		exit()

	if "-ifile=" not in sys.argv[1]:
		print("ERROR not input file parameters passed")
		usage()
		exit()
	if "-ofile=" not in sys.argv[2]:
		print("ERROR no output file parameter passed")
		usage()
		exit()

	ipath = sys.argv[1].split("=")[1]
	opath = sys.argv[2].split("=")[1]

	ToXes(ipath,opath)

if __name__ == "__main__":
	main()
	