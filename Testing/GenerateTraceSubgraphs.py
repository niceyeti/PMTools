"""
The model for this script is that we have generated some data, mined a model from it using process mining
tools, and converted the output petri net (pnml) to a graphml graph for easy reading and traversal. The input
graph must be structured such that nodes represent activities, edges represent sequential transitions between
activities, and the graph must also have a START and END node denoting the entry/exit points.

This script takes as input a path to a graphml file containing the ground-truth process model given by some external
algorithm; it also takes a path to the original trace file from which this model was mined. The traces are then replayed
on the discovered model, where each walk is regarded as a miniature graph. These mini graphs are output to a .g
file which can then be fed to SUBDUE.

The graph edges are assumed to be unlabelled, so the .g file edge listings will not contain that info. Note the difference
between this and the example applications of GBAD/SUBDUE, which often use edge labellings.
"""
from __future__ import print_function
import igraph
import sys

"""
Generates the traces, given the model. Note we are essentially re-generating the traces.

Each trace in the original data file had no known ground truth model: 'ABCD', 'ABDC' contain no known linear information, eg. we could
not assume that these are simply linear graphs such as {St->A, A->B, B->C, C->D, D->End}.
The mined process model, eg {St->A, A->B, B->C, B->D, C->End, D->End}, now gives us an estimate of the underlying model, which 
allows us to reproduce the ground-truth edge relations representing sequential activities (or the best that the mining algorithm provided).

TODO: Its quite possible that certain process discovery algorithms and heuristics may generate an incomplete model, such
that some trace may not be replayed on that model. Not quite clear yet how to handle this.

@graphPath: Path to a graphml path representing the mined process model
@tracePath: Path to some file containing traces in the form [integer],[anomaly status],[observed sequence]. For example, "123,+,ABCD".
@outputPath: The path to which all the walks replayed on the mined model will be stored, in .g format. Each trace is stored as described
in the .g examples: prepended with "XP" or "XN" to indicate anomaly-status, a listing of vertices and info, then a listing of edges and info.
"""
def GenerateTraces(graphPath, tracePath, outputPath):
	#read the mined process model
	model = igraph.Graph.Read(graphPath)
	
	traceFile = open(tracePath,"r")
	gFile = open(outputPath,"w+")
	modelInfo = graph["name"]
	gFile.write("% Trace replay of "+tracePath+" on model mined from "+graphPath+" for model "+modelInfo+"\n\n")
	
	for trace in traceFile.readlines():
		tokens = trace.split(",")
		#detect the anomaly status of this trace
		isAnomalous = "+" == tokens[1]
		traceNo = int(tokens[0])
		sequence = tokens[2]

		#"replay" the sequence on the mined model; bear in mind some model-miners may generate incomplete or inaccurate models,
		#such that every sequence may not be a valid walk on the graph!
		gTrace = ReplaySequence(sequence,model) #returns a list of igraph edges defining this walk
		gRecord = BuildGRecord(isAnomalous,traceNo,gTrace)
		gFile.write(gRecord)
		
	traceFile.close()
	gFile.close()
		
"""
Utility for looking up the edge given by two activitiy labels, a and b.

Returns: edge with edge.sorce = a and edge.target = b. None if not found.
"""
def getEdge(a,b,graph):
	e = None
	for edge in graph.es:
		if graph.vs[edge.source]["name"] == a and graph.vs[edge.target]["name"]:
			e = edge
	return e
		
"""
Given a partially-ordered sequence and a graph (process model) on which to replay the sequence, we replay them to derived
the ground-truth edge transitions (the real ordering) according the given process model. Returns the walk represented by @sequence
according to the graph.

NOTE: The graph (mined process model) may be incomplete or inaccurate, depending on the mining algorithm that generated it. Hence
the sequence may not be a valid walk! I detect and warn about these case because it isn't yet clear how to handle them. For now I will
search across the vertices for the dest vertex of a broken walk; if not found, advance to th next suffix and repeat the search. Continue 
until we find a valid re-entry point, or the sequence is exhausted. 

Note: Also note the complexity of mapping a partially-ordered sequence representing AND, OR, and LOOP constructs. This function
relies on many rules defined in the data generation grammar, such that individual activities may be mapped to edges given the partial-ordering.
The task is not as trivial as it may appear. A given activity 'B' in the sequence 'ABC' may be ambiguous in terms of its predecessor and successor nodes.
Most obviously, it does not necessarily share an edge with its immediate neighbors A and C. Likewise, for purely partial ordered sequences, A could have multiple
predecessors and successors. However, given the petrinet definition, this is not possible: A may have only one predecessor. This constraint is a key
assumption relied on in this function. The constraint means, given A and searching for its in/out edges for this partial ordering,  it is valid to search to
simply search forward for the first node in the po with which A shares an edge, and search backward for the first node which shares an edge with A.

Returns: A list of igraph edges giving the walk represented by this partially ordered sequence and the graph.

@sequence: a sequence of characters representing single activities, partially-ordered
@graph: the igraph on which to 'replay' the partial-ordered sequence, thereby generating the ordered sequence to return
"""		
def ReplaySequence(sequence, graph):

	#init the edge sequence with the edge from START to sequence[0] the first activity
	edgeSequence = []
	initialEdge = getEdge("START", sequence[i])
	if initialEdge == None:
		print("WARNING edgeSequence.len = 0 in ReplaySequence() of GenerateTraceSubgraphs.py. No edge found from START to first activity of "+sequence)
	else:
		edgeSequence.append(initialEdge)
	
	#See the header for this search routines' assumptions. Searches forward for first successor; this is necessarily the next ede
	i = 0
	while i < len(sequence) - 2:
		#search downstream for this activity's edge, given the partial ordering
		j = i + 1
		edge = None
		while j < len(sequence) - 1 and edge == None:
			edge = getEdge(sequence[i], sequence[j])
			j += 1

		if edge != None:
			edgeSequence.append(edge)
		else:
			print("WARNING no edge found for activity: "+sequence[i]+" for sequence "+sequence)
		
		i += 1

	#add the last transition from last activity to the END node
	finalEdge = getEdge(sequence[len(sequence)-1], "END")
	if finalEdge == None:
		print("WARNING no final edge found to END node for sequence: "+sequence)

	return edgeSequence

#Gets a vertex label/name by vertex id/index
def getName(vId,graph):
	return graph.vs[vId]["name"]
	
"""
Given an edge sequence, builds a single .g record in the form given in those files (vertex declaratons, edge list, etc).
The edges are unlabelled.

Returns: A formatted string representing the trace .g record (using directed edge syntax)

@isAnomalous: Whether or not this trace is anomalous
@traceNo: This trace's number.
@gTrace: The list of edges representing this trace
"""
def BuildGRecord(isAnomalous,traceNo,gTrace, graph):
	record = ""
	if isAnomalous:
		record = "XP"
	else:
		record = "XN"
	record += "\n"

	#build the vertex declarations
	vertices = {}
	for edge in gTrace:
		if edge.source not in vertices:
			vertices[edge.source] = graph.vs[edge.source]["name"]
		if edge.target not in vertices:
			vertices[edge.target] = graph.vs[edge.target]["name"]
	for key in vertices:
		record += ("v " + str(key) + " " + vertices[key] + "\n")

	#build the edge declarations
	for edge in gTrace:
		record += ("d " + str(edge.source) + " " + str(edge.target) + "\n") #note that edges have no labels

	return record


def usage():
	print("Usage: python ./GenerateTraceSubgraphs.py [path to graphml model file] [path to trace file] [output path for .g file]")

	
if len(sys.argv) != 4:
	print("ERROR incorrect number of params passed to GenerateTraceSubgraphs.py")
	usage()
	exit()

GenerateTraces(sys.argv[1], sys.argv[2], sys.argv[3])
