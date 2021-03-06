"""
Given some graphml file parameter, reads the graph into an igraph object and generates stochastic traces
by walking the graph from START node to END node according to the distribution parameters defined in the
graph.

The graphml file is expected to contain a graph defined by the output of ModelConverter.py, which outputs
a (possibly cyclic) left to right graph with probability distribution parameters on all edges (although only
the parameters at LOOP and OR nodes are meaningful, since all other edge probabiliies are 1.0). The probabilities
in the graphml may be negative, in which case a passed value --ThetaTraces may be set and used instead.

If --thetaTrace= is passed, then this value is written over all negative @probability values in the stored graph.

Output: A number of traces of the graph, labelled +/-1 to demark whether or not a particular walk traversed any
anomalous edge one or more times. Output format (this was defined by the needs to the client):
	0,-,ABCDEFGH...
	1,+,BCEFHI...

Usage:
	print("python ./DataGenerator -file=(path to graphml file) -n=[number of traces to generate] -ofile=(path to output file; defaults to traces.txt if not passed)]")
	
TODO:
	What are the parameters that should be included? We could instead pass a config file with a bunch
	of required fields: type of statistical distribution to follow, number of traces, anomaly distributions, etc.

"""
import random
import igraph
import sys
import math
import os
import matplotlib.pyplot as plt

class DataGenerator(object):
	def __init__(self):
		self._startNode = None
		self._endNode = None

	"""
	Given some nodeId, returns the igraph-vertex.
	"""
	def _getNode(self,nodeIndex):
		return self._graph.vs[nodeIndex]

	"""
	The utility for generating a single trace from the input graph. This encapsulates a graph walk,
	and hence the probabilistic logic/parameters for choosing walks.
	
	Notes: This method requires that every activity in the model is unique. Also, every AND must be appended with some activity,
	to guarantee that a recursive search down the AND-branches recombine at some node, which can then be found by chopping off
	the non-matching prefixes of these searches. For example, the left and right searches for (ABC&EFG)H gives "ABCH..." and "EFGH...". 
	Given the constraints, the joining node of the AND is H, and can be detected as such, as the first matching char in the left and right strings.
	
	Returns: A list of (igraph-edge,time) tuples, representing all transitions for this trace. The reason for this construction is we need to preserve some of the
	edge info for post-processing analysis, but primarily because AND splits (parallel paths) can't be represented as a string. The 'time' member of the tuple
	represents the discrete timestep at which the edge was walked; since an edge may be walked multiple times (for loops only), an edge may occur multiple times
	in the returned list, albeit with different time-stamps.
	
	TODO: This may need to be simplified with BFS queue or stack-based implementation.
	
	@startNode: The node from which to start the walk.
	@startTime: The discrete time step (some integer) representing the start time for this walk.
	"""
	def _generateTrace(self,startNode, startTime):
		curNode = startNode
		isAnomalousTrace = False
		transitionList = []
		currentTime = startTime
		
		while curNode["label"] != "END":
			#randomly select and follow an outgoing edge from the current node, until we reach the last node; there should be at most 2 outgoing edges for any node
			outEdges = [outEdge for outEdge in self._graph.es if outEdge.source == curNode.index]
			numEdges = len(outEdges)
			edgeTypes = [e["type"] for e in outEdges]
			#print(str(edgeTypes))

			#first, if a LOOP subprocess is represented by one of the edges, probabilistically take it first, since the loop will end back at the current source node, and the probabilistic choice repeats
			#Note: This gives only uniform preference to the LOOP according to its edge-probability; it may be better to define this exponentially, such that the probability of taking the loop decreases exponentially after each iteration
			loopTaken = False
			if "LOOP" in edgeTypes:
				for e in outEdges:
					if e["type"] == "LOOP":
						loopEdge = e
				if not loopEdge["isTraversed"]:
					loopEdge["isTraversed"] = True #mark the loop edge as traversed; this is only required on loop edges, to prevent endless recursion
					pLoop = float(loopEdge["probability"])
					if pLoop > 0.0:
						r = float(random.randint(1,100)) / 100.0
						if r <= pLoop:
							transitionList.append((loopEdge, currentTime))
							if "^_" not in curNode["label"]: # only update time step for non-empty transitions
								currentTime += 1
							curNode = self._graph.vs[loopEdge.target]
							loopTaken = True
			#continue
			
			if not loopTaken:
				#select edge type probabilistically; this must be done now that we add random structure to existing nodes (AND, OR, LOOP)
				#To resolve this, I probabilistically choose which type of structural edges to traverse, then handle them separately
				edgeType = None
				#create a vector of bins, inclusive of all edges/types, by which to select an edge TYPE based on its probability
				choiceEdges = [edge for edge in outEdges if edge["type"] != "LOOP"]
				probs = [edge["probability"] for edge in choiceEdges]
				zNorm = sum(probs)
				probs = [prob/zNorm for prob in probs] #make sure distribution is proper, s.t. all sum to 1.0
				bins = []
				pSum = 0.0
				for i in range(0,len(probs)):
					bins.append((pSum,pSum+probs[i],i))
					pSum+=probs[i]
				r = float(random.randint(1,1000)) / 1000.0 #generates a random float in range 0.001-1.0
				for bin in bins:
					if r >= bin[0] and r <= bin[1]:
						targetIndex = bin[2]
				edgeType = choiceEdges[targetIndex]["type"]
				#print("BINS: "+str(bins))
			
				#after loops, outgoing edges are exclusively AND or OR or SEQ
				if edgeType == "AND":
					outEdges = [edge for edge in outEdges if edge["type"] == "AND"]
					if len(outEdges) < 2: #unrecoverable; all AND splits must have two or more outgoing edges, or something is broken in the model
						print("ERROR out edges for split node < 2: "+str(outEdges)+" model: "+self._model)
						raw_input()
					#firstly, add entry points to each branch to transition list
					transitionList.append((outEdges[0], currentTime))
					transitionList.append((outEdges[1], currentTime))
					currentTime += 1
					#For AND splits, go down both branches, then glue their shared prefixes to get the re-join point of the branches
					leftNode = self._graph.vs[outEdges[0].target]
					leftPath = self._generateTrace(leftNode,currentTime)
					rightNode = self._graph.vs[outEdges[1].target]
					rightPath = self._generateTrace(rightNode, currentTime)

					#TODO: MAKE THIS A FUNCTION
					#make sure this whole search returns index of END node if no match is found; although, we do guarantee each AND split is appended with an alpha
					#find the first char at which the two strings match; on a 'mostly' acyclic graph, this is the node (via its name/label) at which the AND rejoined
					i = 0
					matchFound = False
					#for each char in leftPath, search for match in rightPath
					while i < len(leftPath) and not matchFound:
						j = 0
						while j < len(rightPath) and not matchFound:
							if self._getNode(leftPath[i][0].source)["label"] == self._getNode(rightPath[j][0].source)["label"]:
								matchFound = True
								leftJoinIndex = i
								rightJoinIndex = j
							j += 1
						i += 1
					#returns index of first matching node, which can be proven to be the join-point of the AND split
					leftPrefix = leftPath[0:leftJoinIndex]
					if len(leftPrefix) > 0:
						transitionList += leftPath[0:leftJoinIndex]
					rightPrefix = rightPath[0:rightJoinIndex]
					if len(rightPrefix) > 0:
						transitionList += rightPath[0:rightJoinIndex]
					#restart walk from the Join node, at which the two AND branches rejoined
					curNode = self._graph.vs[leftPath[leftJoinIndex][0].source]
					#for AND splits, the join point of the two paths will occur at time max(time-at-end-of-right-path, time-at-end-of-left-path) + 1
					currentTime = max(rightPath[rightJoinIndex][1], leftPath[leftJoinIndex][1]) + 1
					
					#this should be unreachable, since every AND is appended with some char. Should never reach END node.
					if not matchFound:
						print("ERROR not matchFound in _generate() for AND. "+str(matchFound)+"  node: "+curNode["label"])
				
				#OR split detected, so stochastically choose ANY of available edges to follow based on their probability
				elif edgeType == "OR":
					#create a vector of bins, inclusive of all edges (some could be non-OR type), by which to select an edge based on its probability
					orEdges = [edge for edge in outEdges if edge["type"] == "OR"]
					probs = [edge["probability"] for edge in orEdges]
					zNorm = sum(probs)
					probs = [prob/zNorm for prob in probs] #make sure distribution is proper, s.t. all sum to 1.0
					bins = []
					pSum = 0.0
					for i in range(0,len(probs)):
						bins.append((pSum, pSum+probs[i],i))
						pSum+=probs[i]
					r = float(random.randint(1,1000)) / 1000.0 #generates a random float in range 0.001-1.0
					for bin in bins:
						if r >= bin[0] and r <= bin[1]:
							targetIndex = bin[2]
					randomEdge = orEdges[targetIndex]
						
					transitionList.append((randomEdge,currentTime))
					if "^_" not in curNode["label"]: # only update time step for non-empty transitions
						currentTime += 1
					curNode = self._graph.vs[randomEdge.target]

				#lastly, only one option left: current node has only one outgoing "SEQ edge"
				elif edgeType == "SEQ":
					outEdges = [edge for edge in outEdges if edge["type"] == "SEQ"]
					#detect and notify of more than one SEQ out-edge for a particular node, which is an invalid topology
					if len(outEdges) > 1:
						print("WARNING more than one SEQ edge in _generateTrace(). Num edges: "+str(outEdges))
					transitionList.append((outEdges[0],currentTime))
					if "^_" not in curNode["label"]: # only update time step for non-empty transitions
						currentTime += 1		
					curNode = self._graph.vs[outEdges[0].target]
				else:
					#this else should be unreachable, so notify if not
					print("ERROR unreachable else reached in _generateTrace() for edgeTypes: "+str(edgeTypes))
					transitionList.append((outEdges[0],currentTime))
					if "^_" not in curNode["label"]: # only update time step for non-empty transitions
						currentTime += 1
					curNode = self._graph.vs[outEdges[0].target]
					
		return transitionList
	
	"""
	Builds the graph and stores some of its basic info for querying.
	"""
	def _buildGraph(self, graphmlPath):
		self._graph = igraph.Graph.Read(graphmlPath)
		#find and store the start and end nodes, so we don't have to look them up constantly
		for v in self._graph.vs:
			if v["label"] == "START":
				self._startNode = v
			if v["label"] == "END":
				self._endNode = v
		#store edge-travesal info; this is only so we can detect when a LOOP edge has already been traversed, to prevent endless recursion
		self._graph.es["isTraversed"] = False #mark all edges as not having been walked
	
	"""
	TODO: This function is no longer used, empty transition nodes are just preserved, which shouldn't effect graph compression since the
	pattern will be the same for all edges. If used, this func needs to be re-tested.
	
	Given a list of igraph-edge tuples, performs post-processing after _generateTrace() has completed.
	For now, this only includes resolving empty transitions. The output of _generateTrace() may include walks
	over empty edges (eg, edges labeled "^_123"). This unifies the entry node with the exit node of some empty edge
	transition. An example of an empty transition for three nodes would be A-> ^_123 -> B. This would then unify this
	empty transition to only (A,B), from (A,^_xyz) and (^_xyz, B)
	
	@edges: a list of igraph-edges defining this walk; treat these edges as unordered
	
	Returns: a list of tuples representing the node labels for the walk.
	"""
	def _postProcessEdges(self,edges):
		scrubbed = []

		while len(edges) > 0:
			#not an empty transition edge, so just add it to the output
			if "^" not in [edges[0].source["label"], edges[0].target["label"]]:
				scrubbed += (edges[0].source["label"],edges[0].target["label"])
				edges = edges[1:] #discard the edge after copying it to scrubbed

			#empty transition found, so find the end points of the transition, add these endpoints to the scrubbed list, and remove the empty transitions from edges
			elif "^" in edges[0].target["label"]:
				lambdaLabel = edges[0].target["label"]
				#find the terminal node for the empty branch
				for edge in edges:
					if edge.source["label"] == lambdaLabel:
						sourceEdge = edge
						#warn of contiguous empty branches, which I'm not handling
						if "^" in edge.target["label"]:
							print("WARN contiguous empty branches encountered in _postProcessEdges() of DataGenerator, unhandled")		
				#post-for: have both the start and end points of the empty transition. So add them to scrubbed, and remove them from edge list
				scrubbed += (self._getNode(sourceEdge.source)["label"], self._getNode(edges[0].source)["label"])
				temp = []
				#now filter the edges matching the empty transition we just reconciled
				for edge in edges:
					if lambdaLabel not in [edge.target["label"], edge.source["label"]]:
						temp += edge
				edges = temp

			#same case as prior, but with source/dest reversed. unfortunately this can't be merged with the code in the previous elif
			elif "^" in edges[0].source["label"]:
				sourceLabel = edges[0].source["label"]
				#find the first terminal node for this branch
				for edge in edges:
					if edge.target["label"] == sourceLabel:
						source = edge
						#warn of contiguous empty branches, which I'm not handling
						if "^" in edge.source["label"]:
							print("WARN contiguous empty branch encountered in _postProcessEdges() of DataGenerator, unhandled")		
				#post-for: have both the start and end points of the empty transition. So add them to scrubbed, and remove them from edges
				scrubbed += (source.target["label"], edges[0].target["label"])
				temp = []
				for edge in edges:
					if edge["label"] not in [edges[0].source["label"], dest["label"]]:
						temp += edge
				edges = temp
				
			else:
				print("WARNING unreachable case in _postProcessEdges for edge: "+str(edges[0]))
				scrubbed += (edge.source["label"],edge.target["label"])

		return scrubbed

	"""
	If a trace traverses an AND split, the trace will contain two edges with the same 'source' node for
	the same timestep value (for instance, (A->B,2) and (A->C,2) for some AND split from node A at
	timestep 2). The _writeTrace() function just outputs the 'source' node of every edge in the tracelist,
	so it will output multiple 'A's at some timestep if such edges are not deduplicated.
	
	Hence this function just deduplicates all edges with the same 'source' node and timestep.
	
	@trace: A list of (igraph-edge,time) event tuples.

	Returns: A list of igraph edges, from which 
	"""
	def _deduplicateANDSplits(self, trace):
		filteredTraces = []
		for et in trace: #for event tuple
			#check if this event-tuple et is already in the filteredTraces, based on its timestamp and source node of the edge
			isNewEdge = True
			for fet in filteredTraces:
				#if timestamp and source node match, consider this event tuple a duplicate
				if et[0]["type"] == "AND" and fet[0]["type"] == "AND" and fet[1] == et[1] and fet[0].source == et[0].source:
					isNewEdge = False
			#append this event tuple if it is new
			if isNewEdge:
				filteredTraces.append(et)

		return filteredTraces
				
	"""
	This method sorts activities in traces by their timestep, but does so in a manner that deliberately randomizes
	the order of activities with equal time steps. As noted in _writeTrace() header, this is critical so that we aren'take
	implicitly transmitting model information, such as if a stable sort was used.
	
	The algorithm, however, is very simple:
		0) Completely randomize (shuffle) the traceList T to get R
		1) Stable sort the tracelist by time-step R to get S
	Since (0) achieves randomness w.r.t. all activities with equal time-steps, stable-sorting in (1) is not a problem.

	@trace: A trace list, which is a list of <igraph-edge,integer timestep> tuples.
	
	Returns: None. The input list is sorted in place.
	"""
	def _randomizedSort(self, trace):
		#randomize the traces
		random.shuffle(trace)
		#stable sort the traces
		trace.sort(key=lambda tup : tup[1])
		
		return trace
		
	"""
	Iterates over the activities in a trace and writes the sequence. The traces are assumed to be sorted already.
	The 'source' node of each node in the trace (edge list) is emitted per edge.
	
	Output format:
	To keep the DataGenerator.py cohesive, the traces are output in raw text in the following format. The client
	will have to convert the traces into a target format, such as XES.
	Format:
		+/-,ABCDEF....
	Where the + or - indicates the trace contains at least one anomaly (no other anomaly information is output).
	
	Example trace file:
		-,ABCkhfhsrit
		+,ABCeogjh
		-,ABCdjg
		...
	
	Input:
	@traceNo: The trace number
	@trace: a (potentially unordered) list of (igraph-edges,timeStep) tuples
	@ofile: the output file handle
	"""
	def _writeTrace(self,traceNo,trace,ofile):
		activities = [v["name"] for v in self._graph.vs if v["name"] not in ["START","END"] and "^_" not in v["name"]]
		hasAnomaly = False
		for tup in trace:
			if tup[0]["isAnomalous"]:
				hasAnomaly = True

		ostr = str(traceNo)
		if hasAnomaly:
			ostr += ",+,"
		else:
			ostr += ",-,"

		#remove duplicated AND split source edges (see _deduplicateANDSplits header)
		trace = self._deduplicateANDSplits(trace)
		#Output all the *src* nodes as the activities that occurred at time t, except for the START node of course.
		#By ignoring the target nodes we effectively get only the path bounded between START and END of the walk.
		for edge in trace:
			nodeLabel = self._getNode(edge[0].source)["label"]
			if nodeLabel != "START" and "^_" not in nodeLabel: #ignore STARTn node and empty-transition nodes labeled like "^_123"
				ostr += nodeLabel

				"""
				#add random activity with probability @noiseRate
				if noiseRate > 0.0 and (float(random.randint(1,100)) / 100.0) <= noiseRate:
					#insert a randomly selected activity
					ostr += activities[random.randint(0,len(activities)-1)]
				"""
					
		ofile.write(ostr+"\n")
		
	"""
	Old.
	
	This version outputs the ground-truth edge transitions, which is cheating, since this is what we're assuming we do not
	have. The ground truth is defined as the activity relations, eg A->B. But this may be useful in the future. 
	
	A trace is a uordered list of i-graph edges, representing a walk on a graph. The list must be considered unordered
	since a walk may incude concurrent AND paths which split and rejoin, hence those edges are concurrent and
	there is no linear order to the edges.
	
	Output format:
		Outputs the trace (a graph) in .g format, which is consumable by SUBDUE/GBAD.  The format includes 
		an XP/XN representing a negative/positive anomaly trace (positive if trace contains an anomaly), followed
		by a bunch of vertex declarations, then definitions for directed edges. The data generator does not
		produce named edges, so these do not have edge labels.
		
	Example:
		XP
		v 1 A
		v 2 B
		d 1 2
		d 1 3
		....
		
	@trace: a (potentially unordered) list of (igraph-edges,timeStep) tuples
	@ofile: the output file handle
	def _writeTrace(self,trace,ofile):
		hasAnomaly = False
		ostr = ""

		for tup in trace:
			if tup[0]["isAnomalous"]:
				hasAnomaly = True
	
		#outputs a simple edge format
		#if hasAnomaly:
		#	ostr += "+\n" #print a plus to indicate an anomalous trace
		#else:
		#	ostr += "-\n"
        #
		#for edge in trace:
		#	ofile.write(self._getNode(edge.source)["label"]+"\t"+self._getNode(edge.target)["label"]+"\n")
		#ofile.write("\n")
		
		if hasAnomaly:
			ostr += "XP\n"
		else:
			ostr += "XN\n"
			
		#vertex declarations; here I preserve the igraph vertex id's as the .g indices
		vertexDict = {}
		for tup in trace:
			if tup[0].source not in vertexDict:
				vertexDict[tup[0].source] = self._getNode(tup[0].source)["label"]
			if tup[0].target not in vertexDict:
				vertexDict[tup[0].target] = self._getNode(tup[0].target)["label"]
		for k in vertexDict.iterkeys():
			ostr += ("v "+str(k)+" "+vertexDict[k]+"\n")
			
		#output the edges
		for edge in trace:
			#each edge is output as: "srcId destId timestamp"
			ostr += ("d "+str(edge[0].source)+" "+str(edge[0].target)+" "+str(edge[1])+"\n")
		ostr += "\n"
		
		ofile.write(ostr)
	"""
		
		
	"""
	Once a trace has been generated, this resets the state of the generator so it is ready to generate a new trace.
	"""
	def _reset(self):
		self._graph.es["isTraversed"] = False #in igraph, this assignmnet is applied to all edges
		
	"""
	This goofy operation allows paramerizing the graphml model with different passed values of thetaTraces, for experimentation.
	The iteration is weird since thetaTrace is a bifurcation value p, such that we take one branch with probability p, the other with 1.0 - p.
	Hence you have to iterate all nodes and detect splits along their outgoing edges (choice behavior), and set their outgoing edges (max of
	two) to p and 1.0 - p. Note its therefore critical that no node contain more than two outgoing edges, but this can likely be handled by 
	simply setting each -1.0 probability trace; if only one remains, then only set it to p and don't worry about 1.0 - p.
	
	Multiple signal values will be required if thetaTrace is to be set with more granularity.
	"""
	def _setThetaTrace(self, thetaTrace):
		if thetaTrace < 0 or thetaTrace > 1.0:
			print("ERROR _setThetaTrace not in range [0.0,1.0]: "+str(thetaTrace))	
	
		#see header; must iterate edges per nodes
		for node in self._graph.vs:
			#get this node's out-edges
			edges = self._graph.es.select(_source=node.index)

			#set all theta edges
			for edge in edges:
				if edge["probability"] < 0:
					edge["probability"] = thetaTrace
					
			#normalize all edge probs
			normal = float(sum(edge["probability"] for edge in edges))
			for edge in edges:
				edge["probability"] /= normal
			
			#likely obsolete, but can catch unexpected prob settings
			for edge in edges:
				if edge["probability"] > 1.0:
					print("WARNING PROB > 1.0 DETECT IN _setThetaTrace: " +str(edge["probability"]))				
					
	"""
	Sets the probability of all anomalous edges, which is trivial, since they are marked as such.
	"""
	def _setThetaAnomaly(self, thetaAnomaly):
		if thetaAnomaly < 0 or thetaAnomaly > 1.0:
			print("ERROR _setThetaAnomaly not in range [0.0,1.0]: "+str(thetaAnomaly))
	
		#see header; must iterate edges per nodes
		for node in self._graph.vs:
			#get this node's out-edges
			edges = self._graph.es.select(_source=node.index)
			if sum([1 for edge in edges if edge["isAnomalous"]]) > 0:  #only update if there is at least one anomalous edge; else this will overwrite thetaTrace values
				if len(edges) == 1 and edges[0]["isAnomalous"]:
					edges[0]["probability"] = 1.0 #an exception case: only one outgoing edge, so its probability is 1.0
				else:
					#if len(edges) > 1 and not edges[0]["isAnomalous"] and edges[1]["isAnomalous"]: #if a node has only one out-edge and is anomalous, it is just a sequential sub-acitivity of an existing anomaly, so setting its probability (1.0) is unnecessary
					#This algorithm should cover the node transition probs regardless of the number of outputs, setting two to p and 1-p, or only one to p, if only one output remaining
					#print("Edge Count: "+str(len(edges)))
					#these calcs evenly portion probs over an arbitrary number of edges
					for edge in edges:
						if edge["isAnomalous"]:
							edge["probability"] = thetaAnomaly	#normalization, below, works out the cases for multiple anomalous/non-anomalous edges for all cases
						else:
							edge["probability"] = 1.0 - thetaAnomaly

					#normalize the probs
					normal = float(sum([edge["probability"] for edge in edges]))
					#print("Probs: "+str([edge["probability"] for edge in edges]))
					if normal > 0:
						for edge in edges:
							edge["probability"] /= normal

	#A node is not anomalous if it has only anomalous incoming edges
	def _isAnomalousNode(self, node):
		edges = self._graph.es.select(_target=node.index)
		
		return node["name"] != "START" and sum([1 for edge in edges if edge["isAnomalous"]]) == len(edges)
							
	"""
	Overwrites anomalous nodes in the model with the labels/names of non-anomalous nodes.
	Note that since this is done to the model, this is upstream of trace generation, and these new labels are fixed.
	"""
	def _makeAnomaliesNonUniq(self):
		anomalousActivities = set()
		nonAnomalousActivities = set()
		
		#get the anomalous and non-anomalous node sets
		for node in self._graph.vs:
			if self._isAnomalousNode(node):
				anomalousActivities.add(node["label"])
			else:
				nonAnomalousActivities.add(node["label"])
				
		nonAnomalousActivities = list(nonAnomalousActivities)
		print("ANOMALOUS ACTIVITIES: "+str(anomalousActivities))
		print("NON ANOMALOUS ACTIVITIES: "+str(nonAnomalousActivities))
		
		for node in self._graph.vs:
			if self._isAnomalousNode(node) and "^" not in node["label"]:
				node["label"] = nonAnomalousActivities[ random.randint(0,len(nonAnomalousActivities)-1) ]
				node["name"] = node["label"]

	"""
	Main driver for generating traces.
	
	A trace is a unordered list of <i-graph edges, int> pairs, representing a single walk on a process graph from start
	to complete state. The list must be considered unordered	since a walk may incude concurrent AND paths which
	split and rejoin, hence those edges are concurrent and there is no linear order to the edges.
	
	The edges in the trace are sorted by the time-step of their traversal, which gives the 'ordered' linear output
	of the events, for which the underlying model (the activity edges) is still unknown. THIS IS CRITICALLY IMPORTANT.
	AND-branches represent concurrent subprocesses, for which we MUST assume the underlying structure is unknown.
	For instance, the AND split-join ABC&DEF can emit any permutation of ABCDEF that preserves the order relations
	A<B<C and D<E<F in terms of ordering. Thus, the order of the emitted sequence, eg ADBEFC, contains implicit time step
	data.
	
	Accordingly, this function attempts to make the sequences for concurrent activites as random as possible, using a deliberately
	non-stable sort for activities with equal time step values (representing concurrent/parallel activities). This is required so that
	the order of the model isn't leaking into the output because of a stable sort applied to some sort of regularity in the generated
	traces. *****From a research perspective, this is a very important disclosure*****
	
	@thetaTrace: A value between 0.0 and 1.0. If passed, this parameter will overwrite all negative @probability values in the graph.
	@thetaAnomaly: Overwrites anomalous edge probabilities, which are known because edges are labeled with isAnomalous values
	@useNonUniqAnomalies: If true, anomalous activities in the model will be overwritten (before data generation) with non-anomalous activities, forcing SUBDUE to look
	for structural anomalies, not just potentially trivial-to-find uniquely labeled anomalies
	"""
	def GenerateTraces(self, graphmlPath, n, outputPath="./syntheticTraces.log", thetaTrace=None, thetaAnomaly=None, useNonUniqAnomalies=False):
		if not graphmlPath.endswith(".graphml"):
			print("ERROR graphml path is not a graphml file. Path must end with '.graphml'.")
			return
	
		print("Generating traces...")
		ofile = open(outputPath, "w+")
		self._buildGraph(graphmlPath)
		
		if thetaTrace is not None:
			self._setThetaTrace(thetaTrace) #must be done before thetaAnomaly is written
			
		if thetaAnomaly is not None:
			self._setThetaAnomaly(thetaAnomaly)		

		if useNonUniqAnomalies:
			self._makeAnomaliesNonUniq()
			
		#self._normalizeProbs()
		
		#NOTE: starting at 1 is not arbitrary. Ultimately this guarantees the trace-no labels span 1-n, which is a requirement for GBAD/SUBDUE input files later on
		i = 1
		while i <= n:
			trace = self._generateTrace(self._startNode, 0)
			#sort the activities in the trace, but such that activities with equal timesteps are randomized w.r.t. eachother
			trace = self._randomizedSort(trace)
			#write the trace
			self._writeTrace(i, trace, ofile)
			self._reset()
			i += 1
		print("Trace generation completed and output to "+outputPath+".")
		ofile.close()
		
		self._analyzeLog(outputPath)

	"""
	Performs and stores basic log statistics.
	"""
	def _analyzeLog(self, logPath):
		with open(logPath,"r") as logFile:
			traceDist = {} #dict mapping trace strings (partial orderings) to their respective frequencies
			for line in logFile.readlines():
				partialOrdering = line.split(",")[2].strip()
				if partialOrdering in traceDist.keys():
					traceDist[partialOrdering] += 1
				else:
					traceDist[partialOrdering] = 1
				
			traceDist = sorted(traceDist.items(), key=lambda tup: tup[1], reverse=True)
			ys = [tup[1] for tup in traceDist]
			xs = [i for i in range(len(ys))]
			xlabels = [tup[0][0:10] for tup in traceDist]
			
			baseFolder = os.path.dirname(logPath).strip()
			if len(baseFolder) == 0:
				baseFolder = "."
			print("BASE: >"+baseFolder+"<")
			#plt.xticks(xs, xlabels, rotation="vertical")
			plt.title("Trace Frequency Distribution")
			plt.ylabel("Count")
			plt.xlabel("Partial Ordering Ids")
			plt.plot(xs, ys)
			plt.savefig(baseFolder+os.sep+"traceDistribution.png")
			#plt.show()
			
			with open(baseFolder+os.sep+"traceDistribution.py", "w+") as traceDistFile: #also stores the raw number values, if needed for evaluation later
				traceDistFile.write(str(xs))
				traceDistFile.write(str(ys))

def usage():
	print("python ./DataGenerator\n\t[path to graphml file]\n\t-n=[integer number of traces]\n\t[-ofile=(path to output file; defaults to ./syntheticTraces.log if not passed)]")
	print("Optional: --traceTheta=[float]  This parameter, if passed, will overwrite all negative @probability values\n(for OR and LOOP only presumaby) for transitions stored in the graphml")
"""

"""
def main():
	if len(sys.argv) < 3:
		print("ERROR insufficient number of parameters")
		usage()
		exit()
	if "-n=" not in sys.argv[2]:
		print("ERROR no n parameter passed")
		exit()

	graphFile = sys.argv[1]

	n = int(sys.argv[2].split("=")[1])
	if n <= 1:
		print("ERROR n too small.")
		usage()
		exit()

	useNonUniqAnomalies = False
	thetaTrace = None
	thetaAnomaly = None
	for arg in sys.argv:
		if "--thetaTrace=" in arg:
			thetaTrace = float(arg.split("=")[1])
			if thetaTrace <= 0.0 or thetaTrace > 1.0:
				print("ERROR thetaTrace out of range (0.0,1.0): "+str(thetaTrace))
				thetaTrace = None
		if "--thetaAnomaly=" in arg:
			thetaAnomaly = float(arg.split("=")[1])
			if thetaAnomaly < 0.0 or thetaAnomaly > 1.0:
				print("ERROR thetaAnomaly out of range (0.0,1.0): "+str(thetaAnomaly))
				thetaAnomaly = None
		if "--useNonUniqAnomalies" in arg: #the models contain uniq anomaly labels; this directs that anomalous vertices be overwritten in the model with non-anomalous activities, randomly selected
			useNonUniqAnomalies = True				

	ofile = "./syntheticTraces.log"
	if len(sys.argv) >= 4 and "-ofile=" in sys.argv[3]:
		ofile = sys.argv[3].split("=")[1]

	generator = DataGenerator()
	generator.GenerateTraces(graphFile, n, ofile, thetaTrace, thetaAnomaly, useNonUniqAnomalies)

if __name__ == "__main__":
	main()


