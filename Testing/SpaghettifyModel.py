"""
We wish to test for 'spaghetti-like' models of some kind, which are models with high node degree, lots of edges and non-linear
behavior. One way to do so is to randomly add (directed) edges to a given model G according to some simple constraints.
Edges are added until the avg. node degree of the model reaches some parameter rho, a measure of model "density".

The constraints on adding edges aren't yet well understood according to any real world data. For instance, one might
constrain that edges only be added within local structures, only link upstream nodes to downstream ones (prevent loops),
etc. 

Ideas for spaghetti generation:
1) view actual process data to observe what spaghetti procs look like, statistically
2) add edges under a random distribution, but give higher edge probability to high degree/centrality nodes, to prefer the 20% in the 80/20 rule about worker productivity

Input: A process graph with a START and an END node. The START and END node will not have out/in edges added to them, respectively,
which is a constraint we could evaluate later. But IIRC, some of the traversal algorithms I wrote expect START to have no input edges,
and END to have no outputs, so if we axe the constraint, I'll need to recheck those algs. Think of these vertices as Source and Sink in other
graph algs.
"""

from __future__ import print_function
import sys
import igraph
import random

"""
Returns average node degree of a graph g.
Note this function doesn't care about the distribution of node degrees, only the global mean.
"""
def _getAverageDegree(g):
	return float(len(g.es)) / float(len(g.vs))

"""
Any finite graph has a maximum average degree (rho), defined by the maximum number of 
directed edges for a graph of size n.

In such cases, the maximum average degree is given by (#maximumEdges(#nodes) / #nodes).
Where maximumEdges(g) for a directed graph g is given by n * (n - 1).
"""
def _getMaxRho(g):
	numNodes = float(len(g.vs))
	maxEdges = numNodes * (numNodes - 1.0)
	return maxEdges / numNodes

"""
Simply adds edges between random nodes in the graph until some 
density parameter is reach.

@inputpath: Path to a graphml file.
@outputPath: Path to which the new graph will be saved.
@rho: A density parameter (here, the average node degree of the graph)
"""
def Spaghettify(inputPath, outputPath, rho):
	if inputPath == outputPath:
		print("ERROR inputPath==outputPath in Spaghettify()")
		return

	print("Executing spaghetti on graph "+inputPath+". Output will be written to "+outputPath+".")

	i = 0
	g = igraph.Graph.Read(inputPath)
	density = _getAverageDegree(g)
	print("Input graph density: "+str(density))
	maxRho = _getMaxRho(g)
	#show the input graph
	igraph.plot(g)
	
	#if density < rho, then no changes will be made to the input graph
	if density < rho:
		#this case is perfectly valid, but ought to print something to notify the tester anyway
		print("WARN density < rho in Spaghettify. Input graph "+inputPath+" will not be modified.")
	
	#until density parameter is reached
	while density < rho and density < maxRho:
		#add a random edge
		_addRandomEdge(g)
		density = _getAverageDegree(g)
		i+=1
		if i > 1000:
			print("WARNING i > 1000 in Spaghettify(), may be running forever...")
		
	g.write_graphml(outputPath)
	print("Output graph density: "+str(density))
	igraph.plot(g)
	
"""
Adds an edge between two random nodes.
There are no constraints on the structural characteristics of the edge, the selected nodes are purely random and non-equal.
"""
def _addRandomEdge(g):
	newEdge = False
	i = 0
	
	while not newEdge:
		#select two nodes uniformly at random
		n1 = g.vs[random.randint(0, len(g.vs)-1)].index
		n2 = g.vs[random.randint(0, len(g.vs)-1)].index
		while n1 == n2:  #reselect if nodes are the same
			n2 = g.vs[random.randint(0, len(g.vs)-1)].index
		#make sure we're not adding out edges from END or in-edges to START
		if g.vs[n1]["name"] != "END" and g.vs[n2]["name"] != "START":
			#check if n1->n2 is a new edge
			newEdge = (n1,n2) not in [(e.source, e.target) for e in g.es]
			if newEdge: #edge is new, so just add it
				g.add_edge(n1,n2)
			print(str(i))
		i += 1
		if i > 1000:
			print("WARNING i > 1000 in Spaghettify._addRandomEdge(), may be running forever...")
		
def usage():
	print("Usage: python ./SpaghettifyModel.py -input=[graphml path] -output=[output graphml path] -rho=[average node degree param]")

if len(sys.argv) < 4:
	print("ERROR incorrect number of parameters passed to SpaghettifyModel.py")
	usage()
	exit()

inputModel = sys.argv[1].split("-input=")[1]
outputModel = sys.argv[2].split("-output=")[1]
rho = float(sys.argv[3].split("-rho=")[1])

Spaghettify(inputModel, outputModel, rho)
