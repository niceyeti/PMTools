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
Utility for converting pnml format file into a graphml structure, for easy transmission and storage.

@pnmlPath: Path to a pnml file
@opath: Path to the output location for the graphml representation of the pnml

def Convert(pnmlPath):
	print("Converting graph. Be aware this script only resolves transitions separated by a single place or tau-transition, non-recursively.")
	print("It does not curently resolve consecutive places, if that is a valid construct given in some input petri net.")

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
		places[pId] = pName

	#parse the edge data from the petrinet
	for e in root.findall('./net/page/arc'):
		source = e.get('source')
		target = e.get('target')
		arcs.append((source,target))

	#The algorithm for eliminating/factoring out the places: for each place, find all vertices pointing to it, and to which it points, then use these to bypass the place
	for p in places:
		#for this place, get all its in/outlinks
		inLinks = []
		outLinks = []
		for arc in arcs:
			if arc[1] == p: #this edge (from some transition) points to this place, p
				inLinks.append(arc[0])
			elif arc[0] == p: #this place points to some 
				outLinks.append(arc[1])

		if len(inLinks) == 0:
			print("WARN inLinks length 0 in Convert() for place: "+str(p))
			print(str(outLinks))
		if len(outLinks) == 0:
			print("WARN outLinks length 0 in Convert() for place: "+str(p))
			print(str(inLinks))
		
		#print("p edges: "+str(edges))
		
		#union the in/out links of this place. This is the crux of this algorithm, and may be subject to criticism from the process mining crowd.
		for inLink in inLinks:
			for outLink in outLinks:
				edges.append((inLink,outLink))

	print("pre edges: "+str(edges))
	#the edge list currently contains pnml vIds, which this converts to their corresponding vertex names
	edges = [(vertices[e[0]],vertices[e[1]]) for e in edges]

	#add the vertices to the output graph
	vertexNames = [vertices[vId] for vId in vertices]
	
	print("vertices: "+str(vertexNames))
	print("edges: "+str(edges))
	
	#build the igraph graph object. This is really just used to serialize the graph to graphml
	graph = igraph.Graph(directed=True)
	#add the vertices to the igraph object. igraph will assign them vertex ids.
	graph.add_vertices(vertexNames)
	graph.add_edges(edges) #edges is a sequence of vertex name tuples (source,target). Conveniently, you can pass either name tuples of id tuples to add_edges

	#now search for the start and ending nodes: start nodes are those with no inputs, end nodes are those with no outputs
	startNodes = []
	endNodes = []
	for v in graph.vs:
		isStartNode = True
		isEndNode = True
		for e in graph.es:
			if v.index == e.target: #some node points to this one, hence it cannot be a start node
				isStartNode = False
			if v.index == e.source: #this node points to some other, hence it cannot be an end node
				isEndNode = False
		if isStartNode:
			startNodes.append(v)
		if isEndNode:
			endNodes.append(v)
	#end-loop: start and terminal nodes in-hand, so add a START and END node to bind them
	
	#add the start/end vertices
	graph.add_vertex("START")
	graph.add_vertex("END")
	#and thread them in
	startNode = graph.vs.select(name="START")[0]
	endNode = graph.vs.select(name="END")[0]
	for node in startNodes:
		graph.add_edge(startNode.index,node.index)
	for node in endNodes:
		graph.add_edge(node.index,endNode.index)
	
	graph.vs["label"] = [v["name"] for v in graph.vs]
	
	return graph
"""
	
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
Utility for converting pnml format file into a graphml structure, for easy transmission and storage.


@pnmlPath: Path to a pnml file
@opath: Path to the output location for the graphml representation of the pnml
"""
def Convert(pnmlPath):
	print("Converting graph. Be aware this script only resolves transitions separated by a single place, non-recursively.")
	print("It does not currently resolve consecutive places, if that is a valid construct given in some input petri net.")

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
		if "tau" in vName.lower():
			vName = "TAU_" + vName #mark tau nodes
		vertexDict[vId] = vName

	#add places to the vertex set, labelling them as "PLACE" for later identification
	for p in root.findall('./net/page/place'):
		pId = p.get('id')
		pName = "PLACE_"+p.find('./name/text').text
		vertexDict[pId] = pName

	#parse the edge data from the petrinet
	for e in root.findall('./net/page/arc'):
		source = e.get('source') #these are the text-based node-ids, corresponding with the keys in the vertex dict
		target = e.get('target')
		arcs.append((source,target))

	#in this algorithm, the complete pnml graph is built in-memory, then edges of places and 'tau' transitions are removed
	#through an edge-resolution procedure, such that only actual activity-nodes are left
	#filter the place nodes:
	arcs = _resolveEdges(arcs, vertexDict, "PLACE_")
	#filter any 'tau' nodes; these show up in the output of some mining algorithms
	arcs = _resolveEdges(arcs, vertexDict, "TAU_")
	#the arcs now contain only the set of resolve edges, without places or 'tau' transition-nodes
	
	#get the set of all unique activities
	arcIds = set([arc[0] for arc in arcs]+[arc[1] for arc in arcs])
	activityNames = [vertexDict[arcId] for arcId in arcIds]
	#translate the arcs from id-pairs to vertex-name pairs
	edges = [(vertexDict[arc[0]],vertexDict[arc[1]]) for arc in arcs]

	#build the igraph graph object. This is really just used to serialize the graph to graphml
	graph = igraph.Graph(directed=True)
	#finally, add the filtered graph structure vertices and edges to an igraph
	graph.add_vertices(activityNames)
	graph.add_edges(edges) #edges is a sequence of vertex name tuples (source,target). Conveniently, you can pass either name tuples of id tuples to add_edges

	if "START" not in activityNames and "END" not in activityNames:
		#now search for the start and ending nodes: start nodes are those with no inputs, end nodes are those with no outputs
		startNodes = []
		endNodes = []
		for v in graph.vs:
			isStartNode = True
			isEndNode = True
			for e in graph.es:
				if v.index == e.target: #some node points to this one, hence it cannot be a start node
					isStartNode = False
				if v.index == e.source: #this node points to some other, hence it cannot be an end node
					isEndNode = False
			if isStartNode:
				startNodes.append(v)
			if isEndNode:
				endNodes.append(v)
		#end-loop: start and terminal nodes in-hand, so add a START and END node to bind them
	
		#add the start/end vertices
		graph.add_vertex("START")
		graph.add_vertex("END")
		#and thread them in
		startNode = graph.vs.select(name="START")[0]
		endNode = graph.vs.select(name="END")[0]
		for node in startNodes:
			graph.add_edge(startNode.index,node.index)
		for node in endNodes:
			graph.add_edge(node.index,endNode.index)
	
	#store the activity as both the node name and 'label' attribute
	graph.vs["label"] = [v["name"] for v in graph.vs]
	
	#name the graph
	if len(netName) > 0:
		graph["name"] = netName
	else:
		graph["name"] = "mined-process"
	
	return graph	

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