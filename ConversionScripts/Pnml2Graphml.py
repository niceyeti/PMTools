"""
Converts a pnml file to a graphml graph file. See example.pnml for an example of the pnml format.
This script converts a pnml petrinet with places, transitions, and arcs into our target graph format.
(The nomenclature: in pnml 'places' and 'transitions' are like graph nodes, and 'arcs' are edges.)
We want the ground-truth sequential model of the process, which has no places, only edges between transitions (activities).
So only the arc and transition data is useful; the 'place' data and other pnml data is irrelevant or just provides
structural info. 'Places' are essentially resolved: if P is a place, and given the edge set {A->P, P->B}, this
simplifies to {A->B}.

The output of this script is a graphml-formatted graph for which the nodes represent activities, the edges represent sequential
transitions between activities, and the graph has a START and END node representing the entry/exit points of the overall model.

TODO: May need to provide a visual for the presumed mapping between pnml data and our target graphml structure, for
documentation and research purposes.

So far the idea is to have the data generator generate traces, which are then defined in XES, parsed by an external
process discovery tool whose output is a pnml file defining the ground-truth model given by the traces, according to that
algorithm. This pnml must be converted to graphml so we can read in the graph and walk it, to generate the mini-graphs
as input to SUBDUE.
"""

from __future__ import print_function
import igraph
import platform
import sys
import xml.etree.ElementTree as ET

"""
Given a list of arcs in the form (src<int>, dest<int>) and a vertexDict of <int,string>,
and a filter string, this removes all edges connected to vertices containing the filter string (eg, 'PLACE_').
The resolution procedure then sutures all input edges and output edges from the removed nodes. So logically
is A,B,C have in-links to D, and D has outlinks to E,F,G, and if the filter-string is 'D', then D will be removed
and replaced by direct links from A,B,C to E,F,G.
"""
def _resolveEdges(arcs, vertexDict, filterString):
	placeIds = [pId for pId in vertexDict if filterString in vertexDict[pId]]
	for pId in placeIds:
		#get all outlinked nodes from this place
		outLinkNodes = [arc[1] for arc in arcs if arc[0] == pId]
		#get all inlinked nodes to this place
		inLinkNodes = [arc[0] for arc in arcs if arc[1] == pId]
		#remove all the arcs containing this pId as src or dst
		arcs = [arc for arc in arcs if (pId != arc[0] and pId != arc[1])]
		#add the in-out nodes back in
		for outNode in outLinkNodes:
			for inNode in inLinkNodes:
				arcs.append((inNode,outNode))
	return arcs
	
"""
Utility for converting pnml format file into a graphml structure for easier transmission and storage.

@pnmlPath: Path to a pnml file
@opath: Path to the output location for the graphml representation of the pnml
"""
def Convert(pnmlPath):
	print("Converting graph. Be aware this script only resolves transitions separated by a single place, non-recursively.")
	print("It does not currently resolve consecutive places, if that is a valid construct given in some input petri net.")

	#The following algorithm
	#read the pnml data
	root = ET.parse(pnmlPath).getroot()
	netName = root.find("./net/name/text").text
	vertexDict = {} #vertices are stored temporarily as {id : text}
	places = {} #places are stored as vertices; they are only stored for the purposes of factoring them out of the final graph
	arcs = [] #pnml arcs are stored as a list of tuples, (sourceId<string>, targetId<string>)
	edges = [] #the output edge list for the igraph object

	#store the transitions, which will be a mix of 'tau' constructs and actual activities (eg, "register patient", "discharge patient", etc)
	for t in root.findall('./net/page/transition'):
		vId = t.get('id')
		vName = t.find('./name/text').text
		if 'tau' in vName.lower():
			vName = 'TAU_' + vName #mark tau nodes for detection later
		vertexDict[vId] = vName

	#add places to the vertex set, labelling them as "PLACE" for later identification
	for p in root.findall('./net/page/place'):
		pId = p.get('id')
		pName = 'PLACE_'+p.find('./name/text').text
		vertexDict[pId] = pName

	#parse the edge data from the petrinet
	for e in root.findall('./net/page/arc'):
		source = e.get('source') #these are the text-based node-ids, corresponding with the keys in the vertex dict
		target = e.get('target')
		arcs.append((source,target))
		
	#get the start node id (a source: vertex with no in-links)
	startIds = []
	inlinks = [arc[1] for arc in arcs]
	for vId in vertexDict:
		if vId not in inlinks:
			startIds.append(vId)
	if len(startIds) != 1:
		#detect if more than one start node, which is a structurally defective graph/pnml, and should never happen
		print("WARNING len(startIds) != 1, is "+str(len(startIds))+" in Pnml2Graphml. See code. "+str(startIds))
		"""
		This warning is a result of a defect with the pnml format, or rather with my relying on it (is there another graph format we could use as output of the process miner?)
		Pnml files have provide no topological description of the start node in a process; they only have a graphically 'leftmost' node.
		As a result, the graphs (especially if noise is added to a log) must always contain a defined start/end node.
		Consider multiple paths to resolve:
			1) pnml parsing logic (not clear how, since the pnml format doesn't provide a definition of start/end node)
			2) change to a different process output file type (dont know which exist)
		"""
	startNodeId = startIds[0]
	
	#get the end node id (a sink: vertex with no outlinks)
	endIds = []
	outlinks = [arc[0] for arc in arcs]
	for vId in vertexDict:
		if vId not in outlinks:
			endIds.append(vId)
	if len(endIds) != 1:
		#detect if more than one start node, which is a structurally defective graph/pnml, and should never happend
		print("WARNING len(endIds) != 1, is "+str(len(endIds))+" in Pnml2Graphml. See code.")
	endNodeId = endIds[0]
	
	#re-mark the end and start node text; currently they are TAU_ or PLACE_ typed
	#start with a critical error check; this algorithm REQUIRES the final node detected above is not an activity, hence only a tansition or a place.
	if "TAU_" not in vertexDict[startNodeId] and "PLACE_" not in vertexDict[startNodeId]:
		print("ERROR start node not TAU or PLACE see code")
	if "TAU_" not in vertexDict[endNodeId] and "PLACE_" not in vertexDict[endNodeId]:
		print("ERROR end node not TAU or PLACE see code")
	vertexDict[startNodeId] = "START"
	vertexDict[endNodeId] = "END"

	#get all activities (all non-Tau transitions)
	activities = [vertexDict[vId] for vId in vertexDict if "PLACE_" not in vertexDict[vId] and "TAU_" not in vertexDict[vId]]
	#print("Activities: "+str(activities))
	#print("Vertex dict: "+str(vertexDict))

	#bfs from START node: build an edge list (srcName,dstName) of all edges, such that the edges are between valid activities (non-Tau pnml-transitions)
	edgeList = []
	visited = []
	frontier = [startNodeId]
	while len(frontier) > 0:
		#pop first node on frontier list
		curNodeId = frontier[0]
		if len(frontier) <= 1: #pop
			frontier = []
		else:
			frontier = frontier[1:]

		if curNodeId not in visited:
			#get all immediate outlinks from this node
			outLinks = [arc for arc in arcs if arc[0] == curNodeId]
			#recursively get all activity node ids to which these outlinks point (following all intermediate taus, places, etc)
			successors = _getSuccessorActivityIds(outLinks,arcs,vertexDict,d=0)
			#print(str(successors))
			
			for successor in successors:
				#expand frontier with unvisited nodes
				if successor not in visited:
					frontier.append(successor)
				#add link between nodes
				edgeList.append((vertexDict[curNodeId], vertexDict[successor]))

		#add current node to visited list
		visited.append(curNodeId)

	#activities += ["START","END"]
	#build the igraph graph object. Igraph is just used to serialize the graph to graphml.
	graph = igraph.Graph(directed=True)
	#finally, add the filtered graph structure vertices and edges to an igraph
	graph.add_vertices(activities)
	graph.add_edges(edgeList) #edges is a sequence of vertex name tuples (source,target). Conveniently, you can pass either name tuples of id tuples to add_edges
	#print("edges: "+str(edgeList))
	
	#store the activity as both the node name and 'label' attribute
	graph.vs["label"] = [v["name"] for v in graph.vs]
	
	#name the graph
	if len(netName) > 0:
		graph["name"] = netName
	else:
		graph["name"] = "mined-process"
	
	return graph	
	
"""
A recursive utility for getting all activities attached to a given set of outlinks.

An outlink leads to a place, tau-split, or an activity node. So think of an outlink as a graph
edge that can split at multiple points, like branches to flowers. The flowers are the activities.
Hence this retrieves all activities at the end of some branch, also detecting cycles (should not happen).

Cycles should not occur, since our process-graph definition does not allow self-loops, and this only
goes to the first set of nodes.

@outLinks: The immediate outlinks of a node
@arcs: List of tuples representing node ids
@vertexDict: the dict of id keys and string vertex names
@d: current call depth, for bounding search if cycling

Returns: The ids of the activities at the terminal points of these outlinks
"""
def _getSuccessorActivityIds(outLinks,arcs,vertexDict,d=0):
	activities = []
	
	#recursion depth check: probably cycling
	if d > 40:
		print("WARNING Recursive depth-bound of 20 struck in _getSuccessorActivityIds() of Pnml2Graphml.py!")
		return []
	
	#get all activities at the terminal points of these outlinks
	for outLink in outLinks:
		#if this link leads to a place or a tau node, get the outlinks from that node and recurse on them
		if "TAU_" in vertexDict[outLink[1]] or "PLACE_" in vertexDict[outLink[1]]:
			#get all the outlinks of this successor, and recurse on them
			successorLinks = [arc for arc in arcs if arc[0] == outLink[1]]
			activities += _getSuccessorActivityIds(successorLinks, arcs, vertexDict,d+1)
		#else the success is just a regular place, so add it to list
		else:
			activities.append(outLink[1])

	return activities

"""
Plotting, for visual analysis.
"""
def ShowGraph(graph,opath):
	#the sugiyama layout tends to have the best layout for a cyclic, left-to-right graph, if imperfect
	layout = graph.layout("sugiyama")
	#layout = self._graph.layout("kk") #options: kk, fr, tree, rt
	#see: http://stackoverflow.com/questions/24597523/how-can-one-set-the-size-of-an-igraph-plot
	igraph.plot(graph, opath.replace(".graphml",".png"), layout = layout, bbox = (1000,1000), vertex_size=35, vertex_label_size=15)
	igraph.plot(graph, layout = layout, bbox = (1000,1000), vertex_size=35, vertex_label_size=15)
	#igraph.plot(graph, bbox = (1000,1000), vertex_size=35, vertex_label_size=5,label="name")
	
def usage():
	print("Usage: python Pnml2Graphml.py [input file] [output path for graphml file] [optional: --show to show the graph]")

if len(sys.argv) < 3:
	print("ERROR incorrect number of arguments passed to Pnml2Graphml.py. Exiting.")
	usage()
	exit()

ipath = sys.argv[1]
opath= sys.argv[2]

print("Converting pnml at "+ipath+" to output graphml at "+opath)
transitionGraph = Convert(ipath)

if "--show" in sys.argv:
	ShowGraph(transitionGraph,opath)
	
#defensive programming on windows, for which write_graphml currently breaks (likely this is because of a precompiled exe install of igraph or its components)
if "windows" in platform.system().lower():
	try:
		transitionGraph.write_graphml(opath) #this crashes Python 3.5 under windows with igraph precompiled binaries
	except Exception as e: print(e)  #maybe this will save us? maybe not
else:
	transitionGraph.write_graphml(opath) #this crashes Python 3.5 under windows with igraph precompiled binaries
print("Pnml to graphml conversion complete.")
#print(str(transitionGraph))