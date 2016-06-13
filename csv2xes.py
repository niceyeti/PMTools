"""
Script for converting a csv file to XES format, defined by two columns of the csv.

Most XES schemas of interest to process anomaly detection rely on traces of events characterized
by an actor and an action. This just projects the csv columns reflecting these two determinants, omitting
all other information (date, cost, etc.).


"""
from __future__ import print_function
import sys
import xes

"""
Given a csv file path, and the labels of the resource, activity, and trace label columns,
builds and returns a dictionary of traces. The keys of the dict are the unique trace identifiers,
each of which maps to a value that is an ordered list of events, each event formatted as a pair (resource,activity)
"""
def BuildTraces(inputPath, resourceLabel, activityLabel, traceLabel):
	csvFile = open(inputPath,"r")
	lines = csvFile.readlines()
	csvFile.close()
	
	if resourceLabel not in lines[0] or activityLabel not in lines[0] or traceLabel not in lines[0]:
		print("ERROR resource, activity, or trace column label not found in first row of csv ("+inputPath+"): "+resourceLabel+" "+activityLabel+" "+traceLabel)
		print("Line: "+lines[0])
		return {}

	#get the expected number of tokens per line, to detect poorly formatted csv
	labels = lines[0].strip().split(",")
	numTokens = len(labels)
	#get the column numbers of the resource and activity columns (counting from 0)
	rscCol = -1
	actCol = -1
	traceCol = -1
	try:
		rscCol = labels.index(resourceLabel)
	except:
		print("ERROR resource label >"+resourceLabel+"< not found in csv header")
		return {}
	try:
		actCol = labels.index(activityLabel)
	except:
		print("ERROR activity label >"+activityLabel+"< not found in csv header")
		return {}
	try:
		traceCol = labels.index(traceLabel)
	except:
		print("ERROR trace label >"+traceLabel+"< not found in csv header")
		return {}
	
	print("Cols: "+str(actCol)+" "+str(rscCol)+" "+str(traceCol))
	#iterate and build the traces into a trace dictionary, where key=traceLabel, and value=an ordered list of events
	traceDict = {}
	i = 1
	while i < len(lines):
		if len(lines[i]) > 3:
			tokens = lines[i].strip().split(",")
			if len(tokens) != numTokens:
				print("WARNING irregular number of csv tokens parsed from line "+str(i)+": "+lines[i])
			else:
				traceName = tokens[traceCol]
				resource = tokens[rscCol]
				activity = tokens[actCol]
				event = [resource, activity]
				if traceName not in traceDict.keys():
					traceDict[traceName] = [event]
				else:
					traceDict[traceName].append(event)
		i += 1
		
	return traceDict

def usage():
	print("Usage: ./csv2xes.py [input file] rsc=[csv resource label] act=[csv action label] trc=[csv trace label] [outputFile]")
	print("Example: ./csv2xes.py CallCenterProcess.csv rsc=AgentPosition activity=Operation trc=ServiceID output.xes")
	print("The csv values must match strings in the first row of the csv input file, assuming the first row of the csv file contains the labels for the columnar values.")

def main():
	for arg in sys.argv:
		print(arg)
	if len(sys.argv) < 6:
		print("Incorrect number of arguments: "+str(len(sys.argv)))
		usage()
		return 0
	try:
		inputPath = sys.argv[1]
		resourceLabel = sys.argv[2].split("=")[1].strip()
		activityLabel = sys.argv[3].split("=")[1].strip()
		traceLabel = sys.argv[4].split("=")[1].strip()
		outputPath = sys.argv[5]
		#print(resourceLabel,inputPath,activityLabel,traceLabel,outputPath)
		open(inputPath,"r").close()
		traces = BuildTraces(inputPath,resourceLabel,activityLabel,traceLabel)
		log = xes.Log()
		#add the trace to the xes log, just like in the xes developer's github example
		for traceId in traces.keys():
			t = xes.Trace()
			t.attributes = [xes.Attribute(type="string", key="concept:name", value=traceId)]
			#add the events to the trace
			for event in traces[traceId]:
				e = xes.Event()
				e.attributes = [
					xes.Attribute(type="string", key="concept:name", value=event[1]),
					xes.Attribute(type="string", key="Activity", value=event[1]),
					xes.Attribute(type="string", key="org:resource", value=event[0]),
					xes.Attribute(type="string", key="Actor", value=event[0])
				]
				t.add_event(e)
			#add the trace
			log.add_trace(t)
		log.classifiers = [
			xes.Classifier(name="org:resource",keys="org:resource"),
			xes.Classifier(name="concept:name",keys="concept:name")
		]
		#write the log
		open(outputPath, "w+").write(str(log))
	except IOError:
		print("Input file not found: "+sys.argv[1])

if __name__ == "__main__":
    main()