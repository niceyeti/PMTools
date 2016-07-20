"""
Converts a pnml file to a graphml graph file. See example.pnml for an example of the pnml format.
This script converts a pnml petrinet with places, transitions, and arcs into our target graph format. (Excuse
the nomenclature: in pnml 'places' and 'transitions' are like graph nodes, and 'arcs' are edges.)
We want the ground-truth sequential model of the process, which has no places, only edges between transitions (activities).
So only the arc and transition data is useful; the 'place' data and other pnml data is irrelevant or just provides
structural info. 'Places' are essentially flattened: if P is a place, and given the edge set {A->P, P->B}, this
simplifies to {A->B}.

TODO: May need to provide a visual for the presumed mapping between pnml data and our target graphml structure, for
documentation and research purposes.

So far the idea is to have the data generator generate traces, which are then defined in XES, parsed by an external
process discovery tool whose output is a pnml file defining the ground-truth model given by the traces, according to that
algorithm. This pnml must be converted to graphml so we can read in the graph and walk it, to generate the mini-graphs
as input to SUBDUE.
"""

#TODO; haven't gotten ProM automation up yet
from __future__ import print_function
import igraph
import sys
import xml.etree.ElementTree as ET

"""
Utility for converting pnml format file into a graphml structure, for easy transmission and storage.

@pnmlPath: Path to a pnml file
@opath: Path to the output location for the graphml representation of the pnml
"""
def Convert(pnmlPath):
	#read the pnml data
	root = ET.parse(pnmlPath).getroot()
	vertices = {} #vertices are stored temporarily as {id : text}
	places = {} #places are stored as vertices; they are only stored for the purposes of factoring them out of the final graph
	arcs = [] #pnml arcs are stored as a list of tuples, (sourceId<string>, targetId<string>)
	edges = [] #the output edge list for the igraph object
	
	#read the vertex data; the only pnml nodes we're interested in are 'transitions'
	for t in root.findall('./net/page/transition'):
		vId = t.get('id')
		vName = t.find('./name/text').text
		vertices[vId] = vName
	
	#populate the place dictionary, which is only used for the purposes of transforming the petrinet and factoring out the places
	for p in root.findall('./net/page/place'):
		pId = p.get('id')
		pName = p.find('./name/text').text
		vertices[pId] = pName
		
	#parse the edge data from the petrinet
	for e in root.findall('./net/page/arc'):
		source = e.get('source')
		target = e.get('target')
		arcs.append((source,target))	
	
	#The algorithm for eliminating/factoring out the places: for each place, find all vertices pointing to it, and to which it points, then use these to bypass the place
	for p in places:
		#for this place, find all its in/outlinks
		inLinks = []
		outLinks = []
		for arc in arcs:
			if arc[1] == p: #this edge (from some transition) points to this place, p
				inLinks.append(arc[1])
			if arc[0] == p:
				outLinks.append(arc[0])
		
		if len(inLinks) == 0:
			print("WARN inLinks length 0 in Convert() for place: "+str(p))
			print(str(outLinks))
		if len(outLinks) == 0:
			print("WARN outLinks length 0 in Convert() for place: "+str(p))
			print(str(inLinks))	
		
		#union the in/out links of this place. This is the crux of this algorithm, and may be subject to criticism from the process mining crowd.
		for inLink in inLinks:
			for outLink in outLinks:
				edges.append((inLink,outLink))
	
	#the edge list currently contains pnml vIds, which this converts to their corresponding vertex names
	edges = [tuple(vertices[e[0]],vertices[e[1]]) for e in edges]
	
	#add the vertices to the output graph
	vertexNames = [vertices[vId] for vId in vertices]
	
	#build the igraph graph object. This is really just used to serialize the graph to graphml
	graph = igraph.Graph(directed=True)
	#add the vertices to the igraph object. igraph will assign them vertex ids.
	graph.add_vertices(vertexNames)
	graph.add_edges(edges) #edges is a sequence of vertex name tuples (source,target). Conveniently, you can pass either name tuples of id tuples to add_edges
	
	return graph

def usage():
	print("Usage: python Pnml2Graphml.py [input file] [output path for graphml file]")

if len(sys.argv) != 3:
	print("ERROR incorrect number of arguments passed to Pnml2Graphml.py. Exiting.")
	usage()
	exit()

ipath = sys.argv[1]
opath= sys.argv[2]

print("Converting pnml at "+ipath+" to output graphml at "+opath)
transitionGraph = Convert(ipath)
transitionGraph.write_graphml(opath)
print("Pnml to graphml conversion complete.")
print(str(transitionGraph))