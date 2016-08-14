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
	#vertex name overlap
	s1 = set([v["name"] for v in g1.vs if "^_" not in v["name"]])
	s2 = set([v["name"] for v in g2.vs if "^_" not in v["name"]])
	vsetDifference = s1 - s2
	#raw vertex count comparison
	print("Vertex count:\t"+str(len(s1))+"\t"+str(len(s2)))
	print("s1 vertices: "+str(s1))
	print("s2 vertices: "+str(s2))
	print("Vertex set difference s1 - s2: "+str(vsetDifference))
	#get percentage of names shared by s1 with s2
	pctSharedNames = 100.0 * (1.0 - len(vsetDifference) / float(len(s1)))
	print("\nVertex identity:\t"+str(pctSharedNames)+"% (g1/g2 similarity)")
	print("Edge count:\t"+str(len(g1.es))+"\t"+str(len(g2.es)))
	#get the edge overlap: the number of edges, such as 'A'->'B', shared by both g1 and g2
	es1 = set([(g1.vs[e.source]["name"], g1.vs[e.target]["name"]) for e in g1.es])
	es2 = set([(g2.vs[e.source]["name"], g2.vs[e.target]["name"]) for e in g2.es])
	esetDifference = es1 - es2
	pctSharedEdges = 100.0 * (1.0 - len(esetDifference) / float(len(es1)))
	print("Edge identity:\t"+str(pctSharedEdges)+"% (g1/g2 edge similarity")
	print("Edge set difference s1 - s2: "+str(esetDifference))
	
def Usage():
	print("Usage: python ./GraphCompare.py [primary input graphml path] [second input graphml path]")

if len(sys.argv) != 3:
	print("ERROR incorrect number of arguments")
	Usage()

g1path= sys.argv[1]
g2path = sys.argv[2]
Compare(g1path, g2path)

print("Comparison completed for "+g1path+" "+g2path)
