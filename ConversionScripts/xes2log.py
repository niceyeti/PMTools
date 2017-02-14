"""
This script is somewhat single-purpose, for converting an input xes file, likely a real-world
dataset, to .log format. The .log format uses only alphabetic strings, with single chars for activities:

	1,+,ABCDEFGH...
	
This script takes the traces (lists of events), and formats each one as above, with '-' since these real-world
anomalies must be determined qualitatively. A dictionary is output to activityDict.txt to allow parsing 
the alphabetic chars back into event names in the xes files.

The input xes must have a concept:name field for activity names. 

Input: A real-world xes dataset with concept:name for activity names
Output: A .log file and a dictionary activity.dict for mapping activity chars in the .log back into activity names
"""

from __future__ import print_function
import xml.etree.ElementTree as ET
import sys
import xes
import os

"""
Returns a very simple list of traces, with the traces formatted as:
	['3', [['Pete', 'register request'], ['Mike', 'examine casually'], ...
"""
def ReadXes(path, activityKey=None):
	traceKey = "concept:name"
	if activityKey == None:
		activityKey = "concept:name"
	resourceKey = "org:resource"
	traces = []
	
	tree = ET.parse(path)
	root = tree.getroot()
	#get the namespace prefix; this nuisance has to be prepended to all xpath clauses, as in "{namespace}actor/{namespace}actor/...", but the dict can be passed instead
	ns = ""
	if root.tag != None and root.tag != "":
		print("setting namespace to: "+str(root.tag)[0:root.tag.find("}")+1])
		ns = str(root.tag)[0:root.tag.find("}")+1]

	#just grab the traces/events directly; keep it simple
	for trace in root.findall(ns+'trace'):
		#print("TRACE: "+str(trace))
		#get the name of this trace
		for item in trace.findall(ns+"string"):
			if "key" in item.attrib and item.attrib["key"] == traceKey:
				traceName = item.attrib["value"]
		events = []
		#get and iterate the events in this trace
		for event in trace.findall(ns+"event"):
			#print("EVENT: "+str(event))
			#gets the data defining this event
			for item in event.findall(ns+"string"):
				#print("STRS: "+str(event))
				if "key" in item.attrib:
					#get the resource (typically a person or staff title)
					if item.attrib["key"] == resourceKey:
						eventResource = item.attrib["value"]
					#get the activity
					if item.attrib["key"] == activityKey:
						eventName = item.attrib["value"]
			events += [[eventResource,eventName]]
		traces += [[traceName,events]]
		
	#print("BUILT "+str(len(traces))+" TRACES: ")#+str(traces))
	
	return traces
		
"""
Performs transformation of the traces in xes schema format into .g format.
Input traces are formatted as [<traceName,[<eventResource,eventActivity>]>]

Returns a list of traces formatted as small structures: <traceName, [eventList]>,
where the Events in the event list are defined as labelled graph edges: event = [src,dest,actvityName]

For now, this just sequentially unifies the xes (resource,activity) resources. Thus an xes event log like:

	(1) Bob examineReceipt
	(2) Sarah submitReceipt
	(3) John sendOrder
	...
	
becomes:
	
	START Bob examineReceipt
	Sarah John examineReceipt
	John submitReceipt
	John ... sendOrder
	
Note this function also camel-cases all strings and removes all white space.

@traces: A list of trace, each trace formatted as  ['3', [['Pete', 'register request'], ['Mike', 'examine casually'], 
@activitiesAsEdges: Whether or not to represent activities as edges or as nodes, as befits the target process description
in .g format.
def TransformTraces(traces, activitiesAsEdges=True):
	newTraces = []
	#set up the acitivity/resource index; this allows switching node/edge representations
	if activitiesAsEdges:
		actorIndex = 0
		rscIndex = 1
	else:
		actorIndex = 1
		rscIndex = 0

	i = 0
	while i < len(traces):
		events = traces[i][1]
		newEvents = []

		#initialize the event list; this is important in terms of where how the START node is located
		if activitiesAsEdges:
			newEvents = [["START",events[0][actorIndex].title().replace(" ",""),"BEGIN"]]
		else:
			newEvents = [["START", events[0][actorIndex].title().replace(" ",""), events[0][rscIndex].title().replace(" ","")]]
		
		j = 0
		while j < len(events) : #each event formatted as: [Paul, issueReceipt]
			curActor = events[j][actorIndex].title().replace(" ","")
			if j < len(events) - 1:
				nextActor = events[j+1][actorIndex].title().replace(" ","")
			else:
				nextActor = "END"
			activity = events[j][rscIndex].title().replace(" ","")
			newEvents.append([curActor,nextActor,activity])
			j += 1
		#new event list built, so just add it to the new trace list
		newTraces.append([traces[i][0],newEvents])
		i += 1

	return newTraces
"""
	
	
"""
Traces in .log format are anonymous, so only the raw activities are output in the form of a .log string, while tracking activity name/symbol
mappings in the activityDict.

Outputs traces to .log format. Also outputs the mapping from .log activity symbols to activity names, to activityDict.txt.

@traces: A list of traces formatted as <traceName, [<activityName>]>. Eg., ['3', [['Pete', 'register request'], ['Mike', 'examine casually'], ...

"""		
def WriteTraces(traces, outputPath):
	sep = "\n"
	outputFile = open(outputPath,"w+")
	delim = " "
	vertices = {}
	activities = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0987654321_^$!"
	activityDict = {}

	i = 1
	ts = ""
	for trace in traces:
		ts += str(i)+",-,"
		for event in trace[1]:
			eventName = event[1]
			if eventName not in activityDict:
				activitySymbol = activities[0]
				activityDict[eventName] = activitySymbol
				#pop the activity just used
				if len(activities) > 0:
					activities = activities[1:]
					if len(activities) == 0:
						activities = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0987654321_^$"
						"""
						print("ERROR out of activities!! Cannot convert xes convert .log format. Expand activity symbol list or cry.")
						[print(item) for item in activityDict.items()]
						exit()
						"""
			else:
				activitySymbol = activityDict[eventName]
			ts += activitySymbol
		ts += "\n"
		i += 1
	
	outputFile.write(ts)
	outputFile.close()
	dictFile = open("activityDict.txt","w+")
	#the trick here is that by writing str(dict), one can directly read the dict back into python using eval(dictFile.read())
	dictFile.write(str(activityDict))

def usage():
	print("Usage: python ./xes2log.py [path to .xes input file] [path to output .log file] --activityKey=[the xes activity tag eg, 'concept:name']")

def main():
	#check the params
	if len(sys.argv) < 4:
		usage()
		return 0

	try:
		xesPath = sys.argv[1]
		outputPath = sys.argv[2]
		activityKey = sys.argv[3].split("=")[1]
		open(xesPath,"r").close()
		open(outputPath,"w+").close()
		#get the traces as a list
		traces = ReadXes(xesPath, activityKey)
		print(str(traces)[0:1000])
		WriteTraces(traces, outputPath)
		"""

		if "-dbg" in sys.argv:
			print("TRACES BEFORE TRANSFORM: ")
			for trace in traces:
				print(str(trace))

		traces = TransformTraces(traces,activitiesAsEdges)

		if "-dbg" in sys.argv:
			print("NEW TRACES: ")
			for trace in traces:
				print(str(trace))

		WriteTraces(traces,outputPath)
		"""
	except IOError:
		print("Input file not found: "+sys.argv[1])
		return 0

if __name__ == "__main__":
    main()
