"""
Given a SUBDUE log and a file containing substructure prototypes, this compresses
the subdue log wrt the provide substructures. 

GBAD/SUBDUE output is all text-based, so this is annoying text-based for parsing the substructures
and subgraph log.
"""
from __future__ import print_function
import igraph
import sys
import re
import os

"""
Note this currently only takes the top substructure listed in the .g file.
"""
def Compress(logPath, subsPath, outPath):
	bestSub = _parseBestSubstructure(subsPath)
	print(str(sub))
	
	subgraphs = _buildAllTraces(gLog)
	compressedSubs = _compressAllTraces(subgraphs, bestSub)
	_writeSubs(compressedSubs, outPath)
	
"""
Given a list of sub-graphs stored in igraph.Graph structures, write each one
to a new output file, suitable as input to subdue/gbad.
"""
def _writeSubs(subs, outPath):
	
	
	
"""
Given a trace subgraph from the log and a compressing substructure, 
this compresses the subgraph wrt to the compressing substructure. If
the compressing substructure is not contained within the traceSub,
traceSub is returned unchanged. Else, the compressing substructure is replaced
by a single node "SUB1" with all in/out edges to the substructure sutured
accordingly to SUB1.
"""
def _compressTraceSub(traceSub, compSub):
	compressed = traceSub
	if _traceContainsSubgraph(trace, bestSub):
		#build a new, compressed subgraph from scratch, but keeping the old one's indentifying header
		compressed = igraph.Graph(directed=True)
		#preserve the header
		compressed["header"] = traceSub["header"]
		#use set arithmetic to compress the structures
		bestSubEdgeSet = _getEdgeSet(bestSub)
		traceEdgeSet = _getEdgeSet(traceSub)
		bestSubNodeSet = _getNodeSet(compSub)
		traceNodeSet = _getNodeSet(traceSub)
		
		newVertices = [v for v in traceNodeSet.difference(bestSubNodeSet)]
		print("old vertices: "+str(traceNodeSet))
		print("new vertices: "+str(newVertices))
		newVertices += ["SUB1"] #add the new metanode
		newEdges = []
		#redirects all in-edges to the substructure to point at SUB1, all out-edges from the substructure to point from SUB1
		for e in traceEdgeSet:
			#detect edges in-edges to substructure
			if e[0] not in bestSubNodeSet and e[1] in bestSubNodeSet:
				newEdges.append((e[0],"SUB1"))
			#detect out-edges from substructure
			elif e[0] in bestSubNodeSet and e[1] not in bestSubNodeSet:
				newEdges.append(("SUB1",e[1]))
			#detect edges unconnected to substructure
			elif e[0] not in bestSubNodeSet and e[1] not in bestSubNodeSet:
				newEdges.append(e)
			#lastly, no else: ignore edges internal to the substructure
		
		compressed.add_vertices(newVertices)
		compressed.add_edges(newEdges)

	return traceSub
	
	
def _getEdgeSet(g):
	return set([(g.vs[e[0]]["name"], g.vs[e[1]]["name"]) for e in compSub.es])
	
def _getNodeSet(g):
	return set([v["name"] for v in g.vs])

"""
Detects whether or not a particular trace subgraph contains some compressing substructure.

@subTrace: An igraph representation of a trace in the .g log
@compSub: A compressing substructure also represented as an igraph

Returns: bool
"""
def _traceContainsSubgraph(subTrace, compSub):
	traceNodeSet = _getNodeSet(subTrace)
	compNodeSet = _getNodeSet(compSub)
	traceEdgeSet =  _getEdgeSet(subTrace)
	compEdgeSet = _getEdgeSet(compSub)

	return traceNodeSet.contains(compNodeSet) and traceEdgeSet.contains(compEdgeSet)


"""
Given a list of traces subgraphs, and an instance of the best substructure found by subdue/gbad,
this compresses all subgraph wrt the best substructure. If the trace does not contain the substructure,
the trace is preserved in its current form. If the trace does contain the substructure, then the entire
substructure is replaced with a single node "SUB1", and all in/out edges to/from the structure are woven
into this metanode.
"""
def _compressAllTraces(traceSubs, bestSub)
	compressedSubs = []
	
	for trace in traceSubs:
		compressedSubs.append(_compressTraceSub(trace, bestSub))
		
	return compressedSubs
	
"""
Given a .g log formatted as input to gbad/subdue, builds a 
Note that this will disregard comments in the log.

Returns: A list of subgraphs representing all traces in the log, as igraph.Graphs.
"""
def _buildAllTraces(logPath):
	logFile = open(logPath,"r")
	tempLines = []
	subgList = []
	subHeader = ""
	
	for line in logFile.readlines():
		if "XP " == line[0:4]:
			header = line.rstrip()
			#if tempLines is full, build the last subgraph, and restart tempList for gathering lines with which to build the next one
			if len(tempLines) > 0:
				subsStr = ""
				for ln in tempLines:
					subsStr += ln.rstrip()+"~"
				subsStr += "~" #one extra tilde, per the requirement in the _subDeclarationToGraph() header
				sub = _subDeclarationToGraph(subsStr)
				sub["header"] = header
				tempLines = []
			else:
				tempLines += line
	
	return subgList
	
def 
	




"""
Assumptions: the .g substructures are all "d" edges.

Returns: The best substructure, as an igraph.Graph structure.
"""
def _parseBestSubstructure(subsPath):
	vertexDict = {}
	edges = []
	
	#get the raw subs file string (gbad/subdue output) (replacing linefeeds with some temp pattern makes things easier for re's)
	subsRaw = open(subsPath,"r").read().replace("\n","~")
	#print("raw subs:\n"+subsRaw)
	#find the substructures just given a textual anchor pattern: "Normative Pattern (" followed by stuff, followed by double line-feeds
	start = subsRaw.find("Normative Pattern (")
	#print("start: "+str(start))
	subsRaw = subsRaw[start : subsRaw.find("~~",start)] #gets the "Normative Pattern.*\n\n" string
	#find the precise start of the vertex declarations
	subsRaw = subsRaw[ subsRaw.find("    v ") : ]	
	print("subs raw: "+subsRaw)
	sub = _subDeclarationToGraph(subsRaw)

	return substructure
	
"""
Converts a substructure (subgraph) declaration string in .g format to an igraph.Graph structure.

@subStr: The substructure string (starting with the first "v 1 "node1" and ending with the last edge-declaration),
but with all newlines replaced by tilde (just a parsing trick).

Returns: The igraph.Graph structure representing this substructure, having node "name"/"label" attributes
that coincide with the declared vertex names.
"""
def _subDeclarationToGraph(subStr):
	substructure = igraph.Graph(directed=True)
	
	#within the string, find all the "v" and "d" (edge) declarations
	for line in subsRaw.split("~"):
		ln = line.strip()
		if len(ln) > 2:
			#parse a vertex declaration
			if "v " == ln[0:2]:
				vName = ln.split("\"")[1]
				vId = int(ln.split(" ")[1])
				vertexDict[vId] = vName
			#parse an edge declaration (the labels are meaningless; and all are assumed DIRECTED)
			if "d "== ln[0:2]:
				e = (int(ln.split(" ")[1]), int(ln.split(" ")[2]))
				edges.append(e)

	print(str(edges))
	print(str(vertexDict))
	
	#add all of the vertices
	#substructure.add_vertices(vertexDict.values())
	#add all of the edges (by name)
	edges = [(vertexDict[e[0]], vertexDict[e[1]]) for e in edges]
	vertices = []
	for e in edges:
		vertices.append(e[0])
		vertices.append(e[1])
	vertices = list(set(vertices))
	substructure.add_vertices(vertices)
	#preserve the subdue vertex id's as strings (may be useful to preserve these)
	for v in substructure.vs:
		for k in vertexDict.keys():
			if vertexDict[k] == v["name"]:
				v["subdueId"] = str(k)
	
	substructure.add_edges(edges)
			
	return substructure
			
def usage():
	print("usage: python CompressSubdueLog.py [subgraph .g file] [prototypes file (subdue/gbad text output)] [output location for compressed .g log]")
	print("WARNING make sure input has only single line-feed line terminals (linux style), not windows style!!")
	

if len(sys.argv) != 4:
	print("Incorrect nunm parameters passed to CompressSubdueLog.py.")
	usage()

if "linux" not in os.name.lower():
	print("WARNING non-Linux OS detected. Make sure all input to CompressSubdueLog.py has linux style line endings (single line-feeds),")
	print("not windows style CR+LF. All output will preserve linux-format.")
	
inputLog = sys.argv[1]
subsFile = sys.argv[2]
outputLog = sys.argv[3]

Compress(inputLog, subsFile, outputLog)








