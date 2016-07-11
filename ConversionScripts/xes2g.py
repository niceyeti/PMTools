"""
Converts an XES format file into a .g file as required by GBAD/SUBDUE.

XES have some self-describing qualities, and may contain definitions for many things used throughout a file.
Users of process mining applications typically select which of these defined attributes on which to run their
algorithms.

Typically the two driving attributes are Resource (some item or actor) and Activity (the action that occurred).
So if you think about a bunch of csv log data, projecting the Resource and Activity columns would be what a process
miner would base all of their algorithms off.

So the task for this script will always be to determine what the names for the Resource and Activity columns are.
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
def ReadXes(path):
	traceKey = "concept:name"
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
	"""
	#get the global attributes--Not neeeded for now. Jst grab the traces and events
	for globalElement in root.findall('global')
		definition = globalElement.attrib["scope"]:
		defKVPs = globalElement.findall("./*")
		#get the trace kvps
		if definition = "trace":
				for kvp in defKVPs:
					key = kvp["key"]
					value = kvp["value"]
					print("Got TRACE key+val: "+key+"  "+value)
		elif definition = "event":
				for kvp in defKVPs:
	"""

	#just grab the traces/events directly; keep it simple until the mapping from xes to .g is known better
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
		#print("BUILT TRACES: "+str(traces))
	
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
"""
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
For now expect trace list to be a list of lists. The inner structures are [<trace>] where each <trace> = <name,[<event>]>
were each <event> is defined as [src,dest,edge]
"""		
def WriteTraces(traces, outputPath):
	sep = "\n"
	outputFile = open(outputPath,"w+")
	delim = " "
	vertices = {}

	for trace in traces:
		#build the header info for this trace, in .g format
		ts = "% "+trace[0]+sep+"XP"+sep
		
		#build the vertex table from all event entities in the event list
		vertexId = 1
		for event in trace[1]:
			if event[0] not in vertices:
				vertices[event[0]] = vertexId
				vertexId += 1
			if event[1] not in vertices:
				vertices[event[1]] = vertexId
				vertexId += 1
				
		#now build the output string of vertex id/label key and value pairs, per .g format; ***SUBDUE requires them sorted***
		vertexList = [(vertices[label],label) for label in vertices.keys()]
		vertexList.sort(key = lambda tup : tup[0])
		for v in vertexList:
			ts += ("v"+delim+str(v[0]) + delim + v[1] + sep)

		for event in trace[1]:
			#print("EVENT: "+str(event))
			ts += ("e"+delim+str(vertices[event[0]])+delim+str(vertices[event[1]])+delim+event[2]+sep)
		outputFile.write(ts+sep)
	outputFile.close()
		
def usage():
	print("Usage: python ./xes2g.py [path to .xes input file] [path to output .g file]")
	print("Options: -activities=[edges,nodes]")
	print("The '-activities' parameter defines whether or not activities should be represented as nodes or edges in the .g schema.")
	print("Example: python ./xes2g.py process.xes process.g")

def main():

	#check the params
	if len(sys.argv) < 3:
		usage()
		return 0
	if "-" == sys.argv[1][0]:
		print("ERROR invalid input file parameter")
		usage()
		return 0
	if "-" == sys.argv[2][0]:
		print("ERROR invalid output file parameter")
		usage()
		return 0
		
	try:
		xesPath = sys.argv[1]
		outputPath = sys.argv[2]
		open(xesPath,"r").close()
		open(outputPath,"w+").close()
		activitiesAsEdges = True
		#check for '-activities' parameter value
		for arg in sys.argv:
			if "-activities=" in arg and arg.lower().split("=")[1] == "nodes":
				activitiesAsEdges = False

		#get the traces as a list
		traces = ReadXes(xesPath)

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

	except IOError:
		print("Input file not found: "+sys.argv[1])
		return 0

if __name__ == "__main__":
    main()
