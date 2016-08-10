"""
This is nothing more than a wrapper around a few igraph functions
for comparing two graphs G1 and G2 for similarity. For this project,
this is used to compare the ground-truth generated model and a model
mined by process-mining tools.

Input graphs are expected to be decorated as defined by the basic project schema: vertex "name"/"label" attributes.

Similarity metrics are just ad hoc, and will be added to as needed.
"""
from __future__ import print_function
import sys
import igraph


"""
Just some straightforward graph comparion metrics: size, vertex, and edge overlap.
Note most of these are not symmetric measures, measuring g1's similarity to g2, not vice versa.
"""
def Compare(g1Path, g2Path):
	g1 = igraph.Graph.Read(g1Path)
	g2 = igraph.Graph.Read(g2Path)
	
	print("Graph comparison stats for "+g1Path+" and "+g2Path+". Cols represent g1, g2, respectively.")
	#raw vertex count comparison
	print("Vertex count:\t"+str(len(g1.vs))+"\t"+str(len(g2.vs))+"\t"+str(100.0 * float(len(g1.vs)) / float(len(g2.vs)))+"% (g1/g2 similarity)")
	#vertex name overlap
	s1 = set([v["name"] for v in g1.vs])
	s2 = set([v["name"] for v in g2.vs])
	setDifference = s1 - s2
	#get percentage of names shared by s1 with s2
	pctSharedNames = 100.0 * (1.0 - len(setDifference) / float(len(s1)))
	print("Vertex identity:\t"+str(pctSharedNames))
	print("Edge count:\t"+str(len(g1.es))+"\t"+str(len(g2.es))+"\t"+str(100.0 * float(len(g1.es)) / float(len(g2.es)))+"% (g1/g2 similarity)")
	#get the edge overlap: the number of edges, such as 'A'->'B', shared by both g1 and g2
	es1 = set([(g1.vs[e.source]["name"], g1.vs[e.target]["name"]) for e in g1.es])
	es2 = set([(g2.vs[e.source]["name"], g2.vs[e.target]["name"]) for e in g2.es])
	setDifference = es1 - es2
	pctSharedEdges = 100.0 * (1.0 - len(setDifference) / float(len(es1)))
	print("Edge identity:\t"+str(pctSharedEdges)+"% (g1/g2 edge similarity")

def Usage():
	print("Usage: python ./GraphCompare.py [primary input graphml path] [second input graphml path]")

if len(sys.argv) != 3:
	print("ERROR incorrect number of arguments")
	Usage()

g1path= sys.argv[1]
g2path = sys.argv[2]
Compare(g1path, g2path)
print("exiting")
