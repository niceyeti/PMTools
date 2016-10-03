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

@logPath: The path to some .g log to be compressed
@subsPath: The path to some gbad/subdue output text file containing best substructure prototypes (only the best substructure will be used)
@outPath: The output path for the compressed log
@compSubName: The name for the compressed substructure (eg, SUB1, SUB2... SUBi, where i may denote the number of recursive compressions so far)
"""
def Compress(logPath, subsPath, outPath, compSubName="SUBx",showSub=False):
	print("Running SubdueLogCompressor on "+logPath+" using substructures from "+subsPath)
	print("Outputting compressed log to "+outPath+" with new compressed substructure named: "+compSubName)
	print("NOTE: once reduced to a single vertex (most compressed) substructure, the substructure will be looped to itself.")
	
	bestSub = _parseBestSubstructure(subsPath)
	if showSub:
		layout = bestSub.layout("sugiyama")
		igraph.plot(bestSub, layout = layout, bbox = (1000,1000), vertex_size=35, vertex_label_size=15)
	
	bestSub["name"] = compSubName
	#print(str(bestSub))
	subgraphs = _buildAllTraces(logPath)
	#print("subgraphs:\n"+str(subgraphs)+"\nend subgraphs")
	compressedSubs = _compressAllTraces(subgraphs, bestSub)
	#print("compressed: "+str(compressedSubs)+"\nend compress subgraphs")
	_writeSubs(compressedSubs, outPath)

"""
Given a list of sub-graphs stored in igraph.Graph structures, write each one
to a new output file, suitable as input to subdue/gbad.

@subs: A list of igraph structures representing .g traces
@outPath: The path to which the new .g trace file will be written
"""
def _writeSubs(subs, outPath):
	ofile = open(outPath, "wb+") #the b and encode() notation below are just to force linux line endings

	for sub in subs:
		ofile.write((_sub2GFormatString(sub)+"\n").encode())
	
	ofile.close()

"""
Given a sub-graph .g trace in igraph form, converts the structure into a string formatted
in .g format used by subdue/gbad.

NOTE: This outputs using linux line endings

returns: string representing this subgraph/trace in .g format
"""
def _sub2GFormatString(sub):
	vertexDict = {}
	s = sub["header"]+"\n"
	#build the vertex declarations
	i = 1
	for v in sub.vs:
		s += ("v "+str(i)+" \""+v["name"]+"\"\n")
		vertexDict[v["name"]] = i
		i += 1
		
	#build the edge declarations
	for e in sub.es:
		src = vertexDict[sub.vs[e.source]["name"]]
		dst = vertexDict[sub.vs[e.target]["name"]]
		s+= ("d "+str(src)+" "+str(dst)+" \"e\"\n")
		
	return s.rstrip()

"""
Checks if a sub-graph/trace is equal to some compressing substructure.
This check is used to prevent compressing a graph with only one node--some
compressing substructure--into nothing.
"""
def _traceEqualsSubgraph(subTrace, compSub):
	subNodeSet = _getNodeSet(subTrace)
	compNodeSet = _getNodeSet(compSub)
	subEdgeSet =  _getEdgeSet(subTrace)
	compEdgeSet = _getEdgeSet(compSub)

	#note < and > check for proper subsets
	return len(compNodeSet.difference(subNodeSet)) == 0 and len(compEdgeSet.difference(subEdgeSet)) == 0
	
"""
Given a trace subgraph from the log and a compressing substructure, 
this compresses the subgraph wrt to the compressing substructure. If
the compressing substructure is not contained within the traceSub,
traceSub is returned unchanged. Else, the compressing substructure is replaced
by a single node "SUB1" with all in/out edges to the substructure sutured
accordingly to SUB1.

There are actually three cases:
	1) Trace doesn't contain substructure: so just return trace
	2) Trace properly contains substructure: compress the trace wrt the substructure
	3) Trace equals the substructure: This is an exception/edge case, for which the
	compressing substructure must be returned, with a single loop to itself (since subdue/gbad
	probly requires at least one edge)

@traceSub: a trace/subgraph
@compSub: a prototype substructure by which to attempt to compress traceSub
"""
def _compressTraceSub(traceSub, compSub):
	compressed = traceSub
	if _traceContainsSubgraph(traceSub, compSub):
		#see header: return the compressing substructure with one reflexive loop
		if _traceEqualsSubgraph(traceSub, compSub) and len(compSub.vs) == 1:
			print("MAX COMPRESSION")
			#just copy the sub and add a reflexive loop
			compressed = igraph.Graph(directed=True)
			#preserve the trace header
			compressed["header"] = traceSub["header"]
			compressed["name"] = compSub["name"]
			
			#prepare the compressed sub with a single node and single reflexive edge
			compNodeSet = _getNodeSet(compSub)
			if len(compNodeSet) == 0:
				compressed.add_vertices([compSub["name"]])
			else: #else add whatever vertices the compressed structure already had
				vertices = [v["name"] for v in compSub.vs]
				compressed.add_vertices(vertices)
			
			compEdgeSet = _getEdgeSet(compSub)
			if len(compEdgeSet) == 0:
				#add a single reflexive loop
				compressed.add_edges([(compSub.vs[0]["name"], compSub.vs[0]["name"])])
			else:
				compressed.add_edges(list(compEdgeSet))	
		#trace properly contains the substructure, so compress wrt it
		else:
			#print("CONTAINMENT")
			#build a new, compressed subgraph from scratch, but keeping the old one's indentifying header
			compressed = igraph.Graph(directed=True)
			#preserve the header
			compressed["header"] = traceSub["header"]
			#use set arithmetic to compress the trace wrt the compressing substructure
			compEdgeSet = _getEdgeSet(compSub)
			traceEdgeSet = _getEdgeSet(traceSub)
			compNodeSet = _getNodeSet(compSub)
			traceNodeSet = _getNodeSet(traceSub)
			
			#get new vertices (all vertices minus the compressing ones) by name
			newVertices = [v for v in traceNodeSet.difference(compNodeSet)]
			#print("old vertices: "+str(traceNodeSet))
			#print("new vertices: "+str(newVertices))
			newVertices += [compSub["name"]] #add the new metanode
			newEdges = []
			#build the edge set, redirecting all in-edges to the substructure to point at SUB1, all out-edges from the substructure to point from SUB1
			for e in traceEdgeSet:
				#detect edges incident to substructure
				if e[0] not in compNodeSet and e[1] in compNodeSet:
					newEdges.append((e[0],compSub["name"]))
				#detect out-edges from substructure
				elif e[0] in compNodeSet and e[1] not in compNodeSet:
					newEdges.append((compSub["name"],e[1]))
				#detect edges unconnected to substructure
				elif e[0] not in compNodeSet and e[1] not in compNodeSet:
					newEdges.append(e)
				#lastly, no else: ignore edges internal to the substructure
			
			if len(newVertices) == 0: #tracks a specific defect I had
				print("ERROR newVertices empty in SubdueLogCompressor._compressTraceSub()")
			
			if len(newEdges) < len(newVertices) - 1: #just a potential error, for disconnected graphs
				print("ERROR numEdges < numVertices in SubdueLogCompressor")
				
			#loop the single vertex back to itself when it has reached max compression
			if len(newEdges) == 0 and len(newVertices) == 1:
				#print("reflecting max compressed graph")
				newEdges.append((newVertices[0],newVertices[0]))

			#print(str(newVertices))
			compressed.add_vertices(newVertices)
			#print(str(newEdges))
			compressed.add_edges(newEdges)

	return compressed
	
"""
Given a igraph Graph g representing a subgraph/trace from the gbad input,
returns all edges as a set of named pairs (source, dest).
"""
def _getEdgeSet(g):
	return set([(g.vs[e.source]["name"], g.vs[e.target ]["name"]) for e in g.es])
	
"""
Returns the list of node names in some graph g.
"""
def _getNodeSet(g):
	return set([v["name"] for v in g.vs])

"""
Detects whether or not a particular trace subgraph contains some compressing substructure.

@subTrace: An igraph representation of a trace in the .g log
@compSub: A compressing substructure also represented as an igraph

Returns: True if the subtrace contains (and may be equal to) the compSub
"""
def _traceContainsSubgraph(subTrace, compSub):
	subNodeSet = _getNodeSet(subTrace)
	compNodeSet = _getNodeSet(compSub)
	subEdgeSet =  _getEdgeSet(subTrace)
	compEdgeSet = _getEdgeSet(compSub)

	#print("sub ["+subTrace["header"]+": "+str(subNodeSet)+"\ncomp: "+str(compNodeSet))
	#print("subed: "+str(subEdgeSet)+"\ncomped: "+str(compEdgeSet))
	
	#note < and > check for proper subsets
	return compNodeSet.issubset(subNodeSet) and compEdgeSet.issubset(subEdgeSet)


"""
Given a list of traces subgraphs, and an instance of the best substructure found by subdue/gbad,
this compresses all subgraph wrt the best substructure. If the trace does not contain the substructure,
the trace is preserved in its current form. If the trace does contain the substructure, then the entire
substructure is replaced with a single node "SUB1", and all in/out edges to/from the structure are woven
into this metanode.
"""
def _compressAllTraces(traceSubs, bestSub):
	compressedSubs = []

	for trace in traceSubs:
		compressedSubs.append(_compressTraceSub(trace, bestSub))

	return compressedSubs

"""
Given a .g log formatted as input to gbad/subdue, builds a 
Note that this will disregard comments in the log.

Returns: A list of subgraphs representing all traces in the log, as igraph.Graphs. The vertices of the
subgraphs preserve the gbad input vertex ids in the vertex "subdueId" attribute (eg, g.vs[1]["subdueId"])
"""
def _buildAllTraces(logPath):
	logFile = open(logPath,"r")
	subgList = []
	
	i = 0
	lines = logFile.readlines()
	while i < len(lines):
		line = lines[i]
		#start of subgraph, so spool and consume its contents
		if "XP" == line[0:2]:
			header = line.rstrip()
			i += 1
			tempLines = []
			while i < len(lines) and lines[i][0:2] != "XP":
				tempLines.append(lines[i].rstrip())
				i+=1
			if i < len(lines):
				i-=1

			if len(tempLines) == 0: #just detects a defect I was having with empty traces
				print("WARNING tempLines empty in SubdueLogCompressor._buildAllTraces(), output graph will be empty")

			subsStr = ""
			for ln in tempLines:
				subsStr += (ln.rstrip()+"~")
			subsStr += "~" #one extra tilde, per the requirement in the _subDeclarationToGraph() header
			#print("subs in: "+subsStr)
			sub = _subDeclarationToGraph(subsStr)
			sub["header"] = header
			#print("SUB OUT:\n"+sub["header"]+"\n"+str(sub))
			tempLines = []
			subgList.append(sub)
		else:
			i+=1

	return subgList

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
	if len(subsRaw) < 500:
		print("WARNING Possibly empty substructure file detected. Contents:\n"+subsRaw)
	
	#find the substructures just given a textual anchor pattern: "Normative Pattern (" followed by stuff, followed by double line-feeds
	start = subsRaw.find("Normative Pattern (")
	#print("start: "+str(start))
	subsRaw = subsRaw[start : subsRaw.find("~~",start)] #gets the "Normative Pattern.*\n\n" string
	#find the precise start of the vertex declarations
	subsRaw = subsRaw[ subsRaw.find("    v ") : ]	
	#print("subs raw: "+subsRaw)
	sub = _subDeclarationToGraph(subsRaw)

	return sub
	
"""
Converts a substructure (subgraph) declaration string in .g format to an igraph.Graph structure.

@subStr: The substructure string (starting with the first "v 1 "node1" and ending with the last edge-declaration),
but with all newlines replaced by tilde (just a parsing trick).

Returns: The igraph.Graph structure representing this substructure, having node "name"/"label" attributes
that coincide with the declared vertex names.
"""
def _subDeclarationToGraph(subStr):
	substructure = igraph.Graph(directed=True)
	vertexDict = {}
	edges = []
	
	#within the string, find all the "v" and "d" (edge) declarations
	for line in subStr.split("~"):
		ln = line.strip()
		if len(ln) > 2:
			#parse a vertex declaration
			if "v " == ln[0:2]:
				vName = ln.split("\"")[1]
				vId = int(ln.split(" ")[1])
				vertexDict[vId] = vName
			#parse an edge declaration (the labels are meaningless; and all are assumed DIRECTED)
			elif "d "== ln[0:2]:
				e = (int(ln.split(" ")[1]), int(ln.split(" ")[2]))
				edges.append(e)

	#print(str(edges))
	#print(str(vertexDict))
	
	#add all of the vertices
	#substructure.add_vertices(vertexDict.values())
	#add all of the edges (by name)
	edges = [(vertexDict[e[0]], vertexDict[e[1]]) for e in edges]
	vertices = []
	for e in edges:
		vertices.append(e[0])
		vertices.append(e[1])
	vertices = list(set(vertices))
	#print("adding vertices: "+str(vertices))
	substructure.add_vertices(vertices)
	#preserve the subdue vertex id's as strings (it may be useful to preserve these)
	for v in substructure.vs:
		for k in vertexDict.keys():
			if vertexDict[k] == v["name"]:
				v["subdueId"] = str(k)
	
	#copy name as label attributes of vertices for display
	for v in substructure.vs:
		v["label"] = v["name"]
	
	#print("adding edges: "+str(edges))
	substructure.add_edges(edges)
			
	return substructure
			
def usage():
	print("usage: python SubdueLogCompressor.py [subgraph .g file] [substructure prototype file (subdue/gbad text output)] [output path for compressed .g log] [optional: name=name of compressed structure]")
	print("--showSub: pass to display the parsed substructure")
	print("WARNING make sure input has only single line-feed line terminals (linux style), not windows style!!")
	

if len(sys.argv) < 4:
	for arg in sys.argv:
		print(arg)
	print("Incorrect num parameters ("+str(len(sys.argv))+") passed to SubdueLogCompressor.py.")
	usage()
	exit()

if "linux" not in os.name.lower():
	print("WARNING non-Linux OS detected. Make sure all input to SubdueLogCompressor.py has linux style line endings (single line-feeds),")
	print("not windows style CR+LF. All output will preserve linux-format.")

inputLog = sys.argv[1]
subsFile = sys.argv[2]
outputLog = sys.argv[3]
if len(sys.argv) > 4 and "name=" in sys.argv[4]:
	compSubName = sys.argv[4].split("=")[1]
else:
	compSubName = "SUBx"

showSub = "--showSub" in sys.argv
	
Compress(inputLog, subsFile, outputLog, compSubName, showSub)
