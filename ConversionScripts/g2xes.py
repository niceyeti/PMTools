"""
Small script for converting an activity information-flow graph in .g format to XES, the eXtenible Event Stream format
consumable by many process mining applications.

".g" files have the following format (this is o2g output):

	% 159
	XP
	v 1 Customer
	v 2 Sales
	v 3 Warehouse
	e 1 2 Order
	e 2 3 InternalOrder
	e 2 1 OrderAcknowledgement
	e 3 1 DeliveryNote

	% 160
	XP
	v 1 Customer
	v 2 Sales
	v 3 Warehouse
	e 1 2 Order
	e 2 3 InternalOrder
	e 2 1 OrderAcknowledgement
	e 3 1 DeliveryNote

An alternative representation may use vertices to represent activities, instead of resources,
as such:

	% 159
	XP
	v 1 START
	v 2 Order
	v 3 InternalOrder
	v 4 OrderAcknowledgment
	v 5 DeliveryNote
	v 6 END
	e 0 1 Customer
	e 1 2 Sales
	...
If this representation is used in the input .g file, it must be indicated by passing the -actNodes flag. Note that
the START and END vertices are required. The default assumes the format at top, above, for which vertices
are resources and edges are activities.
	
In all cases, assume that execution of processes is given by the order of the edges.
"""

from __future__ import print_function
import sys
import xes
import copy

def usage():
	print("Usage: python ./g2xes.py [path to .g input file] [path to output file] [optional process name]")
	print("Example: python ./g2xes.py process.g process.xes ")
	
"""
Builds a trace list from a .g file.

The trace list is a list containing 4-ples of trace name, number, vertex dictionary, edge list.
(number, name, vertex dict, edge list)

The vertex dictionary maps integer vertex ids to their names: {id : name}
The edge list contains integer src and dest vertex ids, and a label: (src, dest, activity)
The trace name is whatever is the line led by '% ' in the .g file at the top of each trace.
The trace number is just the sequential numbr of the trace as it occurred in the .g file, starting from 0.
"""
def BuildTraceList(inputPath):
	vertices = {}
	edges = []  #edges will be stored as list of tuples: (vertex source id, vertex dest id, activity)
	name = ""
	traceNo = 0
	traces = []
	
	inputFile = open(inputPath,"r")
	#iteratively builds the vertex dictionary {vertex id: name string} and edge list from the .g data, and add them to the trace list
	for rline in inputFile.readlines():
		line = rline.strip()
		#when empty line found, add the previous trace, then clear the trace structure
		if len(line) == 0:
			traces += [[traceNo + 1, traceNote.strip(), traceVertices, traceEvents]]
			traceNo += 1
		if len(line.strip()) >= 2:
			tokens = line.split(" ")
			#store the trace header as the trace's name
			if line[0] == "%":
				traceNote = line[2:].strip()
				traceVertices = {}
				traceEvents = []
			#store a vertex
			if line[0:2] == "v ":
				if len(tokens) == 3:
					id = int(tokens[1])
					name = tokens[2]
					traceVertices[id] = name
				else:
					print("ERROR failed to parse vertex tokens from vertex line: "+line)
			#store an edge
			if line[0:2] == "e ":
				if len(tokens) == 4:
					src = int(tokens[1])
					dest = int(tokens[2])
					activity = tokens[3]
					traceEvents += [(src,dest,activity)]
					#validate the vertex ids:
					if src not in traceVertices or dest not in traceVertices:
						print("ERROR vertex id of edge not found in vertex dict for trace number "+str(traceNo)+" for line: "+line)
				else:
					print("ERROR Incorrect number of tokens from event line: "+line+" Make sure the event names contain no spaces.")

	traces += [[traceNo + 1, traceNote.strip(), traceVertices, traceEvents]]

	#print("Parsed "+str(traceNo)+"/"+str(len(traces))+" from file: "+inputPath)
	
	return traces
	
"""
Transforms the traces output by BuildTraceList() into flat traces. This function is just
meant to output something equivalent to the examples in the python xes docs and from the py xes
developers github examples. However, I'll keep the trace number and name attributes, even though 
his/her example doesn't include that info. It should be added later to the xes.

Input: a traceList as described by BuildTraceList() as a list of tuples formatted as (trcNumber, trcName, vertex dict, edge list)
and each edge in edgeList is simply (source<int>,dest<int>,activity).

Returns: list of traces formatted as lists of dictionaries, as
   traces = [
        [ traceNumber, traceName,
            [{"concept:name" : "Register", "org:resource" : "Bob"},
             {"concept:name" : "Negotiate", "org:resource" : "Sally"},
             {"concept:name" : "Negotiate", "org:resource" : "Sally"},
             {"concept:name" : "Sign", "org:resource" : "Dan"},
             {"concept:name" : "Sendoff", "org:resource" : "Mary"}
			]
			[ {"concept:name" : "Register", "org:resource" : "Bob"},
			...
			],
		...
		]
"""
def FormatTraceList(traceList,activitiesAsNodes):
	outputList = []
	#each trace stored as structures: (number, name, vertex dict, edge list)
	for trace in traceList:
		newTrace = [trace[0],trace[1],[]]
		#build each xes 'event' from the edge list
		for edge in trace[3]:
			#get the source, dest, and activity; these may be used (or not used) quite differently according to the data representation we want
			src = trace[2][edge[0]]
			dest = trace[2][edge[1]]
			activity = edge[2]	
			#define and add the event
			newTrace[2].append({"concept:name" : activity, "org:resource" : src})
		outputList += [newTrace]

	return outputList
	
"""
Write out the process log data to xes. This is taken directly from the xes-module developer's page.
"""
def WriteXes(traces, outputPath):
		log = xes.Log()
		#print("TRACES: "+str(traces))
		#add the trace to the xes log, just like in the xes developer's github example
		for trace in traces:
			t = xes.Trace()
			t.attributes = [xes.Attribute(type="string", key="concept:name", value=trace[1])]
			#add the events to the trace
			for event in trace[2]:
				e = xes.Event()
				e.attributes = [
					xes.Attribute(type="string", key="concept:name", value=event["concept:name"]),
					xes.Attribute(type="string", key="Activity", value=event["concept:name"]),
					xes.Attribute(type="string", key="org:resource", value=event["org:resource"]),
					xes.Attribute(type="string", key="Actor", value=event["org:resource"])
				]
				t.add_event(e)
			#add the trace
			log.add_trace(t)
		log.classifiers = [
			xes.Classifier(name="org:resource",keys="org:resource"),
			xes.Classifier(name="concept:name",keys="concept:name")
		]
		#write the log
		of = open(outputPath, "w+")
		of.write(str(log))
		of.close()
	
def main():
	if len(sys.argv) < 3:
		print("Incorrect number of arguments: "+str(len(sys.argv)))
		usage()
		return 0

	try:
		inputPath = sys.argv[1]
		open(inputPath,"r").close()
		outputPath = sys.argv[2]
		traceList = BuildTraceList(inputPath)
		traces = FormatTraceList(traceList, activitiesAsNodes)
		WriteXes(traces, outputPath)
		
	except IOError:
		print("Input file not found: "+sys.argv[1])

	return 0

if __name__ == "__main__":
    main()

"""
   traces = [
        [
            {"concept:name" : "Register", "org:resource" : "Bob"},
            {"concept:name" : "Negotiate", "org:resource" : "Sally"},
            {"concept:name" : "Negotiate", "org:resource" : "Sally"},
            {"concept:name" : "Sign", "org:resource" : "Dan"},
            {"concept:name" : "Sendoff", "org:resource" : "Mary"}
        ],
        [
            {"concept:name" : "Register", "org:resource" : "Bob"},
            {"concept:name" : "Negotiate", "org:resource" : "Sally"},
            {"concept:name" : "Sign", "org:resource" : "Dan"},
            {"concept:name" : "Sendoff", "org:resource" : "Mary"}
        ],
        [
            {"concept:name" : "Register", "org:resource" : "Bob"},
            {"concept:name" : "Negotiate", "org:resource" : "Sally"},
            {"concept:name" : "Sign", "org:resource" : "Dan"},
            {"concept:name" : "Negotiate", "org:resource" : "Sally"},
            {"concept:name" : "Sendoff", "org:resource" : "Mary"}
        ],
        [
            {"concept:name" : "Register", "org:resource" : "Bob"},
            {"concept:name" : "Sign", "org:resource" : "Dan"},
            {"concept:name" : "Sendoff", "org:resource" : "Mary"}
        ]
    ]

    log = xes.Log()
    for trace in traces:
        t = xes.Trace()
        for event in trace:
            e = xes.Event()
            e.attributes = [
                xes.Attribute(type="string", key="concept:name", value=event["concept:name"]),
                xes.Attribute(type="string", key="org:resource", value=event["org:resource"])
            ]
            t.add_event(e)
        log.add_trace(t)
    log.classifiers = [
        xes.Classifier(name="org:resource",keys="org:resource"),
        xes.Classifier(name="concept:name",keys="concept:name")
    ]

    open("example.xes", "w").write(str(log))
"""