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

"""
Note this currently only takes the top substructure listed in the .g file.
"""
def Compress(gLog, subsPath, outPath):
	sub = _parseBestSubstructure(subsPath)
	print(str(sub))
	
	
	

	
	
	



"""
Assumptions: the .g substructures are all "d" edges.

Returns: The best substructure, as an igraph.Graph structure.
"""
def _parseBestSubstructure(subsPath):
	substructure = igraph.Graph(directed=True)
	vertexDict = {}
	edges = []
	
	#get the raw subs file string (gbad/subdue output) (replacing linefeeds with some temp pattern makes things easier for re's)
	subsRaw = open(subsPath,"r").read().replace("\n","~")
	#print("raw subs:\n"+subsRaw)
	#find the substructures just given a textual anchor pattern: "Normative Pattern (" followed by stuff, followed by double line-feeds
	start = subsRaw.find("Normative Pattern (")
	#print("start: "+str(start))
	subsRaw = subsRaw[start : subsRaw.find("~~",start)] #gets the "Normative Pattern.*\n\n" string
	print("subs raw: "+subsRaw)
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
	substructure.add_edges(edges)
	
	return substructure
	
			
			
			
def usage():
	print("usage: python CompressSubdueLog.py [subgraph .g file] [prototypes file (subdue/gbad text output)] [output location for compressed .g log]")

	
	
	


if len(sys.argv) != 4:
	print("Incorrect nunm parameters passed to CompressSubdueLog.py.")
	usage()
	
inputLog = sys.argv[1]
subsFile = sys.argv[2]
outputLog = sys.argv[3]
Compress(inputLog, subsFile, outputLog)








