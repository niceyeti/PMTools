"""
The model for this script is that we have generated some data, mined a model from it using process mining
tools, and converted the output petri net (pnml) to a graphml graph for easy reading and traversal. The input
graph must be structured such that nodes represent activities, edges represent sequential transitions between
activities, and the graph must also have a START and END node denoting the entry/exit points.

(Academic) NOTE: This method does not obey the petri-net formalism. The generic petri-net mined from the log data could
feasibly support more behavior than is generated here, because of the 'firing' of places/transitions on a petri net. However,
this project assumed the process had a ground-truth graphical model of single-step temporal transitions. So this is only valid
because of the assumptions that are made about the upstream ground-truth synthetic model.


This script takes as input a path to a graphml file containing the process model given by some external
algorithm; it also takes a path to the original trace file from which this model was mined. The traces are then replayed
on the discovered model, where each walk is regarded as a miniature graph. These mini graphs are output to a .g
file which can then be fed to SUBDUE.

This script also outputs the markov model of the traces to markovModel.py in the provided output directory.

The graph edges are assumed to be unlabelled, so the .g file edge listings will not contain that info. Note the difference
between this and the example applications of GBAD/SUBDUE, which often use edge labellings.
"""
from __future__ import print_function
import igraph
import sys
import os

"""
Oddly named, but this object's responsibility is reading in a model graphml file, and a file containing
test traces, and replaying each trace on the model to generate a big record to be passed to SUBDUE or
GBAD in their respective formats. Note that each trace is replayed and output as its own 'XP'/'XN' graph.
"""
class Retracer(object):
	def __init__(self):
		pass
        
	"""
	The markov model is initialized not just from the edges encountered in the log, but from the underlying mined model, even if
	edge transitions are zero. Just by including zero frequency edges doesn't interfere with the model; such edges are needed
	later when processing distributions based on the markov model as a process model.
	
	NOTE: This function requires that _readModel() has executed and constructed the edge model
	"""
	def _initializeMarkovModel(self):
        #init the markov model, for which keys = string pairs, vals = transition count
		self._markovModel = dict()
		
		#iterate the edges as a sequence of named transitions ('a', 'b')
		for edgeTup in self._edgeMap.keys():
			self._markovModel[edgeTup] = 0
		
	"""
	Generates the traces, given the model. Note we are essentially re-generating the traces.

	Each trace in the original data file had no known ground truth model: 'ABCD', 'ABDC' contain no known linear information, eg. we could
	not assume that these are simply linear graphs such as {St->A, A->B, B->C, C->D, D->End}.
	The mined process model, eg {St->A, A->B, B->C, B->D, C->End, D->End}, now gives us an estimate of the underlying model, which 
	allows us to reproduce the ground-truth edge relations representing sequential activities (or the best that the mining algorithm provided).

	TODO: Its quite possible that certain process discovery algorithms and heuristics may generate an incomplete model, such
	that some trace may not be replayabe that model. Not quite clear yet how to handle this.

	@graphPath: Path to a graphml path representing the mined process model
	@tracePath: Path to some .log file containing traces in the form [integer],[anomaly status],[observed sequence]. For example, "123,+,ABCD".
	@outputPath: The path to which all the walks replayed on the mined model will be stored, in .g format. Each trace is stored as described
	in the .g examples: prepended with "XP" or "XN" to indicate anomaly-status, a listing of vertices and info, then a listing of edges and info.
	@useSubdueFormat: A bool indicating whether or not to output SUBDUE or GBAD formatted traces. I'm trying to keep the schema for either
	the same, they just use different syntax. The graphs/groups.g file in SUBDUE provides the guiding example of the target format in which traces
	will be output by this class.
	"""
	def GenerateTraces(self, graphPath, tracePath, outputPath, useSubdueFormat, subgraphPath):
		print("Retracer subgraph-generator replaying traces from "+tracePath+" on mined model "+graphPath+". Output will be saved to "+outputPath)

		self._readModel(graphPath)
		self._initializeMarkovModel()
		traceFile = open(tracePath,"r")
		gFile = open(outputPath,"w+")
		#output the subgraphs representing each individual trace to subgraphs.py
		#subgraphPath = os.path.dirname(outputPath)
		#if len(subgraphPath) <= 2:
		#	subgraphPath = "./"
		#subgraphPath += "/subgraphs.py"
		#print("\n\nOPENING SUBSGRAPHS: "+subgraphPath)
		subgraphFile = open(subgraphPath,"w+")
		modelInfo = self._model["name"]

		#write header info, for convenience
		header = "Trace replay of "+tracePath+" on model mined from "+graphPath+" for model "+modelInfo+"\n"
		if useSubdueFormat:
			header = "%" + header
		else:
			header = "//" + header
		gFile.write(header)

		#prepare and write all of the traces to the target format
		self._outputTraces(traceFile, gFile, useSubdueFormat, subgraphFile)
        
		markovFile = outputPath[:outputPath.rfind("/")]+"/markovModel.py"
		print("Outputting markov model to: "+markovFile)
		
		self._writeMarkovModel(markovFile)
        
		subgraphFile.close()
		traceFile.close()
		gFile.close()

	def _writeMarkovModel(self, outputPath):
		f = open(outputPath,"w+")
		print("\n\n>>>MARKOV MODEL: "+str(self._markovModel))
		f.write(str(self._markovModel))
		f.close()

	"""
	Reads in a graph from graphml into an igraph graph object, and also caches the vertex and edge mappings in the object
	for faster lookups compared with iterating the igraph vertex/edge linear sequences, which can be incredibly slow for frequent
	graph traversals.
	"""
	def _readModel(self, gpath):
	#read the mined process model
		print("Reading graph from "+gpath)
		self._model = igraph.Graph.Read(gpath)

		#edgeMap maps symbolic (activity1, activity2) name string tuples directly to igraph edges
		self._edgeMap = {}
		#revMap maps igraph edges directly back to the (activity1, actvitiy2) named tuples keys of edgeMap
		self._edgeRevMap = {}
		for edge in self._model.es:
			key = (self._model.vs[edge.source]["name"], self._model.vs[edge.target]["name"])
			self._edgeMap[key] = edge
			self._edgeRevMap[edge] = key

	"""
	Utility for looking up the edge given by two activitiy labels, a and b.

	Returns: edge with edge.sorce = a and edge.target = b. None if not found.
	"""
	def _getEdge(self,srcName,dstName):
		#look up the edge via the (srcName, dstName) tuple uniquely identifying an edge
		eId = (srcName,dstName)
		if (srcName,dstName) in self._edgeMap.keys():
			return self._edgeMap[eId]
		else:
		#print("ERROR no edge found for "+str(eId))
			return None
	"""
		e = None
		for edge in graph.es:
			if graph.vs[edge.source]["name"] == a and graph.vs[edge.target]["name"] == b:
				e = edge
		return e
        """

	"""
	In special cases, one wants to use this object's capabilities to simply convert a .log file to a gbad file, such
	as when noise has been added to the original log after generating it, and we want to regenerate a gbad/subdue file.
	
	This function takes a .log file and directly converts it to gbad format, without trace generation. Since the log contains noise, 
	"""
		
		
	"""
	Outputs the traces in SUBDUE format, just like the 'groups.g' example found in the graphs/ folder of subdue.
	
	@traceFile: a .log file
	@gFile: the .g file to which traces will be written (as graphs)
	@useSubdueFormat: use subdue format over gbad
	@subgraphFile: The file to which each trace-graph will be written as a tuple, the first member the trace id, the second item the list of edges representing the graph
	"""
	def _outputTraces(self, traceFile, gFile, useSubdueFormat, subgraphFile):
		traces = [line.strip() for line in traceFile.readlines() if len(line.strip()) > 0]
		ntraces = str(len(traces))
		ctr = 0
		for trace in traces:
			if ctr % 100 == 99:
				print("\rEmitting trace: "+str(ctr)+" / "+ntraces+" traces                                      ",end="")
			ctr += 1
			tokens = trace.split(",")
			#detect the anomaly status of this trace
			isAnomalous = "+" == tokens[1]
			traceNo = int(tokens[0])
			sequence = tokens[2]

			#"replay" the sequence on the mined model; bear in mind some model-miners may generate incomplete or inaccurate models,
			#such that every sequence may not be a valid walk on the graph!
			gTrace = self._replaySequence(sequence) #returns a list of igraph edges defining this walk
			if useSubdueFormat:
				print("SUBDUE FORMAT TODO. EXITING")
				exit()
				gRecord = self._buildSubdueRecord(isAnomalous, traceNo, gTrace)
			else:
				gRecord = self._buildGbadRecord(isAnomalous, traceNo, gTrace)
			gFile.write(gRecord)
			
			#also write the graph representation of the trace to the subgraphs.py file, for processing later in python
			self._writeSubgraph(subgraphFile, traceNo, gTrace, includeEndPoints=False)
            
			self._updateMarkovModel(gTrace)
            
		print("  Done.")

	"""
	Writes python representation of graph to file, as a tuple: tup[0]=traceNo, tup[1] = list of edges as named tuples, as in [('a', 'c'), ('f', 'h'), ('a', 'h')]
	
	@subgraphFile: Open file handle to which the edge sequence will be written
	@traceNo: The trace number
	@gTrace: A list of named tuples representing the edge sequence given by some graph: [('a', 'c'), ('f', 'h'), ('a', 'h') ... ]
	@includeEndPoints: Whether or not to include the START and END nodes of each trace
	"""
	def _writeSubgraph(self, subgraphFile, traceNo, gTrace, includeEndPoints=False):
		s = "("+str(traceNo)+","
		
		#filter end points if not requested to include them
		if not includeEndPoints:
			edgeList = [edge for edge in gTrace if edge[0].upper() not in {"START","END"} and edge[1].upper() not in {"START","END"}]
		
		#edgeList = [(gTrace.vs[e.source]["name"], gTrace.vs[e.target]["name"])  for e in gTrace.es]
		s += str(edgeList)
		s += ")\n"
		
		subgraphFile.write(s)
		
	"""
	Accepts a list of edges code as a list of directed edge pairs: [('a','b'), ('c','f'), ... ]
	and update in-memory markov model.
	"""
	def _updateMarkovModel(self, edgeSequence):
		for edge in edgeSequence:
			if edge in self._markovModel.keys():
				self._markovModel[edge] += 1
			else:
				#this should be unreachable, based on constructing the markov model from the all-behavior-inclusive process model, so warn if reached
				#the justification for this warning is that no edge should be detected that is not included in the model already; if there is, either the log
				#was modified (? maybe to add noise), or an error has occurred, so it needs to be justified why this was reached
				print("\n\n>>> WARNING: new edge detected in _updateMarkovModel not found in original graph: "+str(edge))
				self._markovModel[edge] = 1
        
	"""
	Converts an igraph edge into an activity tuple
	
	@edge: an igraph edge
	@graph: the graph from which this edge came
	"""
	def _edgeToActivityTuple(self, edge):
		#return (graph.vs[edge.source]["name"], graph.vs[edge.target]["name"])
		return self._edgeRevMap[edge]
		
	"""
	Given a partially-ordered sequence and a graph (process model) on which to replay the sequence, we replay them to derive
	the ground-truth edge transitions (the real ordering) according the given process model. Returns the walk represented by @sequence
	according to the graph.

	NOTE: The graph (mined process model) may be incomplete or inaccurate, depending on the mining algorithm that generated it. Hence
	the sequence may not be a valid walk! I detect and warn about these cases because it isn't yet clear how to handle them. For now,
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
	def _replaySequence(self, sequence):
		activitySet = set([v["name"] for v in self._model.vs])
		#init the edge sequence with the edge from START to sequence[0] the first activity
		edgeSequence = []
		initialEdge = self._getEdge("START", sequence[0])
		if initialEdge == None:
			print("First node="+str(self._model.vs[0]["name"]))
			print("ERROR edgeSequence.len = 0 in _replaySequence() of GenerateTraceSubgraphs.py. No edge found from START to first activity of "+sequence)
		else:
			e = self._edgeToActivityTuple(initialEdge)
			edgeSequence.append(e)

		#See the header for this search routines' assumptions. Searches forward for first successor; this is necessarily the next edge
		i = 0
		while i < len(sequence) - 1:
			#handles insertion anomalies: for which the log contains an activity not in the model
			if sequence[i] not in activitySet:
				#arbitrarily attach sequence[i] activity to immediately-previous activity
				if i == 0:
					e = ("START",sequence[i])
				else:
					e = (sequence[i-1],sequence[i])
				edgeSequence.append(e)
			else:
				#search downstream for this activity's edge, given the partial ordering
				j = i + 1
				edge = None
				while j < len(sequence) and edge == None:
					edge = self._getEdge(sequence[i], sequence[j])
					#edge = self._getEdge(sequence[i], sequence[j], graph)
					j += 1

				#Above loop only looks for links up to end of sequence, but excluding END. If we've reached end of sequence w/out finding
				#an edge, it may be because this activity links directly to END. This if-stmt handles this case
				if j == len(sequence) and edge == None and self._getEdge(sequence[i], "END") is not None:
					#activity links to END node
					edge = self._getEdge(sequence[i], "END")

				if edge != None:
					e = self._edgeToActivityTuple(edge)
					edgeSequence.append(e)
				else:
					#this case occurs when, for instance, an activity in the activity-set is anomalously repeated in some out-of-order way, inconsistent with the mined-model
					print("WARNING no outgoing edge found from activity: "+sequence[i]+" for sequence "+sequence)
					activity = sequence[i]
					if i < len(sequence) - 1:
						nextActivity = sequence[i+1]
					else:
						nextActivity = "END"
					print("Arbitrarily associating activity with next in partial ordering: "+activity+"->"+nextActivity)
					edgeSequence.append((activity, nextActivity))
			i += 1

		#add the last transition from last activity to the END node
		finalEdge = self._getEdge(sequence[len(sequence)-1], "END")
		if finalEdge == None:
			print("WARNING no final edge found from activity "+sequence[len(sequence)-1]+"->END node for sequence >"+sequence+"<.")
			print("Appending arbitrary link.")
			edgeSequence.append((sequence[len(sequence)-1],"END"))
		else:
			e = self._edgeToActivityTuple(finalEdge)
			edgeSequence.append(e)

		return edgeSequence

		"""
		OBSOLETE
		"""
	def _buildSubdueRecord(self, isAnomalous, traceNo, gTrace):
		vertexCounter = 1
		record = ""
		if isAnomalous:
			record = "XP\n%"+str(traceNo)+"\n"
		else:
			record = "XN\n%"+str(traceNo)+"\n"

		vertices = {} #maps vertexName->vertexId, where vertexId is newly assigned by the vertexCounter to fit the gbad/subdue scheme
		for edge in gTrace:
			srcName = self._model.vs[edge.source]["name"]
			if srcName not in vertices:
				vertices[srcName] = vertexCounter
				vertexCounter += 1
			tgtName = self._model.vs[edge.target]["name"]
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
			srcName = self._model.vs[edge.source]["name"]
			tgtName = self._model.vs[edge.target]["name"]
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
	print("Usage: python ./GenerateTraceSubgraphs.py --graphml=[path to graphml model file] --tracePath=[path to trace file] --outputPath=[output path for .g file] --traceGraphs=[path to which graph of each trace written] [--subdue/--gbad (target format)]")

def main():
	if len(sys.argv) < 5:
		print("ERROR incorrect number of params passed to GenerateTraceSubgraphs.py")
		usage()
		exit()

	modelGraphmlPath = None
	tracePath = None
	outputPath = None
	traceGraphPath = None

	for arg in sys.argv:
		if "--graphml=" in arg:
			modelGraphmlPath = arg.split("=")[1]
		if "--tracePath=" in arg:
			tracePath = arg.split("=")[1]
		if "--outputPath=" in arg:
			outputPath = arg.split("=")[1]
		if "--traceGraphs=" in arg:
			traceGraphPath = arg.split("=")[1]
			
	if not modelGraphmlPath or not tracePath or not outputPath or not traceGraphPath:
		print("\n\nERROR retracer missing arguments, in GenerateTraceSubgraphs.py.\n")
		usage()
		exit()

	#use gbad by default; subdue likely not supported, as gbad has been used so much instead
	useSubdueFormat = "--subdue" in sys.argv and not "--gbad" in sys.argv

	retracer = Retracer()
	retracer.GenerateTraces(modelGraphmlPath, tracePath, outputPath, useSubdueFormat, traceGraphPath)

if __name__ == "__main__":
	main()
