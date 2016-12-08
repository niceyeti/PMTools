"""
The model for this script is that we have generated some data, mined a model from it using process mining
tools, and converted the output petri net (pnml) to a graphml graph for easy reading and traversal. The input
graph must be structured such that nodes represent activities, edges represent sequential transitions between
activities, and the graph must also have a START and END node denoting the entry/exit points.

This script takes as input a path to a graphml file containing the process model given by some external
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
Oddly named, but this object's responsibility is reading in a model graphml file, and a file containing
test traces, and replaying each trace on the model to generate a big record to be passed to SUBDUE or
GBAD in their respective formats. Note that each trace is replayed and output as its own 'XP'/'XN' graph.
"""
class Retracer(object):
	def __init__(self):
		pass

	"""
	Generates the traces, given the model. Note we are essentially re-generating the traces.

	Each trace in the original data file had no known ground truth model: 'ABCD', 'ABDC' contain no known linear information, eg. we could
	not assume that these are simply linear graphs such as {St->A, A->B, B->C, C->D, D->End}.
	The mined process model, eg {St->A, A->B, B->C, B->D, C->End, D->End}, now gives us an estimate of the underlying model, which 
	allows us to reproduce the ground-truth edge relations representing sequential activities (or the best that the mining algorithm provided).

	TODO: Its quite possible that certain process discovery algorithms and heuristics may generate an incomplete model, such
	that some trace may not be replayed on that model. Not quite clear yet how to handle this.

	@graphPath: Path to a graphml path representing the mined process model
	@tracePath: Path to some .log file containing traces in the form [integer],[anomaly status],[observed sequence]. For example, "123,+,ABCD".
	@outputPath: The path to which all the walks replayed on the mined model will be stored, in .g format. Each trace is stored as described
	in the .g examples: prepended with "XP" or "XN" to indicate anomaly-status, a listing of vertices and info, then a listing of edges and info.
	@useSubdueFormat: A bool indicating whether or not to output SUBDUE or GBAD formatted traces. I'm trying to keep the schema for either
	the same, they just use different syntax. The graphs/groups.g file in SUBDUE provides the guiding example of the target format in which traces
	will be output by this class.
	"""
	def GenerateTraces(self, graphPath, tracePath, outputPath, useSubdueFormat):
		print("Retracer subgraph-generator replaying traces from "+tracePath+" on mined model "+modelGraphmlPath+". Output will be saved to "+outputPath)

		#read the mined process model
		model = igraph.Graph.Read(graphPath)
		traceFile = open(tracePath,"r")
		gFile = open(outputPath,"w+")
		modelInfo = model["name"]

		#write header info, for convenience
		header = "Trace replay of "+tracePath+" on model mined from "+graphPath+" for model "+modelInfo+"\n"
		if useSubdueFormat:
			header = "%" + header
		else:
			header = "//" + header
		gFile.write(header)

		#prepare and write all of the traces to the target format
		self._outputTraces(traceFile, model, gFile, useSubdueFormat)

		traceFile.close()
		gFile.close()
			
	"""
	Utility for looking up the edge given by two activitiy labels, a and b.

	Returns: edge with edge.sorce = a and edge.target = b. None if not found.
	"""
	def _getEdge(self,a,b,graph):
		e = None
		for edge in graph.es:
			if graph.vs[edge.source]["name"] == a and graph.vs[edge.target]["name"] == b:
				e = edge
		return e

	"""
	Outputs the traces in SUBDUE format, just like the 'groups.g' example found in the graphs/ folder of subdue.
	
	@traceFile: a .log file
	@model: an igraph mined graphical model of the underlying process
	@gFile: the .g file to which traces will be written (as graphs)
	@useSubdueFormat: use subdue format over gbad
	"""
	def _outputTraces(self, traceFile, model, gFile, useSubdueFormat):
		for trace in traceFile.readlines():
			tokens = trace.strip().split(",")
			#detect the anomaly status of this trace
			isAnomalous = "+" == tokens[1]
			traceNo = int(tokens[0])
			sequence = tokens[2]

			#"replay" the sequence on the mined model; bear in mind some model-miners may generate incomplete or inaccurate models,
			#such that every sequence may not be a valid walk on the graph!
			gTrace = self._replaySequence(sequence,model) #returns a list of igraph edges defining this walk
			if useSubdueFormat:
				print("SUBDUE FORMAT TODO. EXITING")
				exit()
				gRecord = self._buildSubdueRecord(isAnomalous, traceNo, gTrace, model)
			else:
				gRecord = self._buildGbadRecord(isAnomalous, traceNo, gTrace)
			gFile.write(gRecord)

	"""
	Converts an igraph edge into an activity tuple
	
	@edge: an igraph edge
	@graph: the graph from which this edge came
	"""
	def _edgeToActivityTuple(self, edge, graph):
		return (graph.vs[edge.source]["name"], graph.vs[edge.target]["name"])
		
	"""
	Given a partially-ordered sequence and a graph (process model) on which to replay the sequence, we replay them to derived
	the ground-truth edge transitions (the real ordering) according the given process model. Returns the walk represented by @sequence
	according to the graph.

	NOTE: The graph (mined process model) may be incomplete or inaccurate, depending on the mining algorithm that generated it. Hence
	the sequence may not be a valid walk! I detect and warn about these case because it isn't yet clear how to handle them. For now I will
	search across the vertices for the dest vertex of a broken walk; if not found, advance to the next suffix and repeat the search. Continue 
	until we find a valid re-entry point, or the sequence is exhausted. If the symbol is not an activity in the graph activities, consider this an insertion-anomaly,
	and output an edge to it, and continue.

	Note: Also note the complexity of mapping a partially-ordered sequence representing AND, OR, and LOOP constructs. This function
	relies on many rules defined in the data generation grammar, such that individual activities may be mapped to edges given the partial-ordering.
	The task is not as trivial as it may appear. A given activity 'B' in the sequence 'ABC' may be ambiguous in terms of its predecessor and successor nodes.
	Most obviously, it does not necessarily share an edge with its immediate neighbors A and C. Likewise, for purely partial ordered sequences, A could have multiple
	predecessors and successors. However, given the petrinet definition, this is not possible: A may have only one predecessor. ***This constraint is a key
	assumption relied on in this function***. The constraint means, given A and searching for its in/out edges for this partial ordering (p.o.),  it is valid to search to
	simply search forward for the first node in the p.o. with which A shares an edge, and search backward for the first node which shares an edge with A.

	Returns: A list of activity tuples representing a direct edge between them: [('a','b'), ('c','f'), ... ]

	@sequence: a sequence of characters representing single activities, partially-ordered
	@graph: the igraph on which to 'replay' the partial-ordered sequence, thereby generating the ordered sequence to return
	"""
	def _replaySequence(self, sequence, graph):
		#init the edge sequence with the edge from START to sequence[0] the first activity
		edgeSequence = []
		initialEdge = self._getEdge("START", sequence[0], graph)
		if initialEdge == None:
			print("WARNING edgeSequence.len = 0 in _replaySequence() of GenerateTraceSubgraphs.py. No edge found from START to first activity of "+sequence)
		else:
			e = self._edgeToActivityTuple(initialEdge, graph)
			edgeSequence.append( e )
		
		#See the header for this search routines' assumptions. Searches forward for first successor; this is necessarily the next edge
		i = 0
		while i < len(sequence) - 1:
			#search downstream for this activity's edge, given the partial ordering
			j = i + 1
			edge = None
			while j < len(sequence) and edge == None:
				edge = self._getEdge(sequence[i], sequence[j], graph)
				j += 1
				
			if edge != None:
				e = self._edgeToActivityTuple(edge, graph)
				edgeSequence.append(e)
			else:
				print("WARNING no edge found for activity: "+sequence[i]+" for sequence "+sequence)
				
			i += 1

		#add the last transition from last activity to the END node
		finalEdge = self._getEdge(sequence[len(sequence)-1], "END", graph)
		if finalEdge == None:
			print("WARNING no final edge found to END node for sequence >"+sequence+"<")
		else:
			e = self._edgeToActivityTuple(finalEdge, graph)
			edgeSequence.append(e)

		return edgeSequence

		"""
		OBSOLETE
		"""
	def _buildSubdueRecord(self, isAnomalous, traceNo, gTrace, graph):
		vertexCounter = 1
		record = ""
		if isAnomalous:
			record = "XP\n%"+str(traceNo)+"\n"
		else:
			record = "XN\n%"+str(traceNo)+"\n"

		vertices = {} #maps vertexName->vertexId, where vertexId is newly assigned by the vertexCounter to fit the gbad/subdue scheme
		for edge in gTrace:
			srcName = graph.vs[edge.source]["name"]
			if srcName not in vertices:
				vertices[srcName] = vertexCounter
				vertexCounter += 1
			tgtName = graph.vs[edge.target]["name"]
			if tgtName not in vertices:
				vertices[tgtName] = vertexCounter
				vertexCounter += 1

		vertexList = [(key,vertices[key]) for key in vertices]
		vertexList.sort(key = lambda v : v[1]) #sort vertices by the new ids (gbad/subdue require ordered, incrementing id sequences)
		#output the vertex declarations
		for tup in vertexList:
			record += ("v " + str(tup[1]) + " " + tup[0] + "\n")

		#build the edge declarations
		for edge in gTrace:
			srcName = graph.vs[edge.source]["name"]
			tgtName = graph.vs[edge.target]["name"]
			record += ("d " + str(vertices[srcName]) + " " + str(vertices[tgtName]) + "\n")
			
		return record

		
	"""
	OBSOLETE
	Given an edge sequence, builds a single .g record in the form given in those files (vertex declaratons, edge list, etc).
	The edges are unlabelled.

	Returns: A formatted string representing the trace .g record (using directed edge syntax)

	@isAnomalous: Whether or not this trace is anomalous
	@traceNo: This trace's number.
	@gTrace: The list of edges representing this trace, as igraph-edges
	def _buildGbadRecord(self, isAnomalous, traceNo, gTrace, graph):
		vertexCounter = 1
		#XP is essentially a dont-care in gbad, but the docs say it is required formatting
		record = "XP # "+str(traceNo)+"\n"

		vertices = {} #maps vertexName->vertexId, where vertexId is newly assigned by the vertexCounter to fit the gbad/subdue scheme
		
		for edge in gTrace:
			srcName = graph.vs[edge.source]["name"]
			if srcName not in vertices:
				vertices[srcName] = vertexCounter
				vertexCounter += 1
			tgtName = graph.vs[edge.target]["name"]
			if tgtName not in vertices:
				vertices[tgtName] = vertexCounter
				vertexCounter += 1

		#output the vertex declarations
		vertexList = [(key,vertices[key]) for key in vertices]
		vertexList.sort(key = lambda v : v[1]) #sort vertices by the new ids (gbad/subdue require ordered, incrementing id sequences)
		#output the vertex declarations
		for tup in vertexList:
			record += ("v " + str(tup[1]) + " \"" + tup[0] + "\"\n")

		#build the edge declarations
		for edge in gTrace:
			srcName = graph.vs[edge.source]["name"]
			tgtName = graph.vs[edge.target]["name"]
			record += ("d " + str(vertices[srcName]) + " " + str(vertices[tgtName]) + " \"e\"\n") #put a "e" label on every edge, just to satisfy gbad. This label could have leverage in the future

		return record
	"""
	
	"""
	Given an edge sequence, builds a single .g record in the form given in those files (vertex declaratons, edge list, etc).
	The edges are unlabelled.

	Returns: A formatted string representing the trace .g record (using directed edge syntax)

	@gTrace: A list of directed edges, represent as tuples: [('A','B'),('C','B') ... ]
	"""
	def _buildGbadRecord(self, isAnomalous, traceNo, gTrace):
		vertexCounter = 1
		#XP is essentially a dont-care in gbad, but the docs say it is required formatting
		record = "XP # "+str(traceNo)+"\n"
		
		#get the set of activities
		activities = []
		for e in gTrace:
			activities += [e[0],e[1]]
		uniqActivities = set(activities)
		
		#build the vertex map
		vertices = {} #maps vertexName->vertexId, where vertexId is newly assigned by the vertexCounter to fit the gbad/subdue scheme
		for activity in uniqActivities:
			vertices[activity] = vertexCounter
			vertexCounter += 1

		#output the vertex declarations
		vertexList = [(key,vertices[key]) for key in vertices]
		vertexList.sort(key = lambda v : v[1]) #sort vertices by the new ids (gbad/subdue require id sequences sorted ascending, starting at 1)
		#output the vertex declarations
		for tup in vertexList:
			record += ("v " + str(tup[1]) + " \"" + tup[0] + "\"\n")

		#build the edge declarations
		for e in gTrace:
			record += ("d " + str(vertices[e[0]]) + " " + str(vertices[e[1]]) + " \"e\"\n") #put a "e" label on every edge, just to satisfy gbad. This label could have leverage in the future

		return record

def usage():
	print("Usage: python ./GenerateTraceSubgraphs.py [path to graphml model file] [path to trace file] [output path for .g file] [--subdue/--gbad (target format)]")

if len(sys.argv) < 4:
	print("ERROR incorrect number of params passed to GenerateTraceSubgraphs.py")
	usage()
	exit()
	
modelGraphmlPath = sys.argv[1]
tracePath = sys.argv[2]
outputPath  = sys.argv[3]
useSubdueFormat = len(sys.argv) == 5 and "--subdue" in sys.argv[4]

retracer = Retracer()
retracer.GenerateTraces(modelGraphmlPath, tracePath, outputPath, useSubdueFormat)
