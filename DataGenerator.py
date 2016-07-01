"""
Given some graphml file parameter, reads the graph into an igraph object and generates stochastic traces
by walking the graph from START node to END node according to the distribution parameters defined in the
graph itself.

The graphml file is expected to contain a graph defined by the output of ModelConverter.py, which outputs
a (possibly cyclic) left to right graph with probability distribution parameters on all edges (although only
the parameters at LOOP and OR nodes are meaningful, since all other edge probabiliies are 1.0).

Output: A number of traces of the graph, labelled +/-1 to demark whether or not a particular walk is traversed any
anomalous edge one or more times.

Usage:
	python DataGenerator.py [path to graphml file] -n=[number of traces to generate]
	
TODO:
	What are the parameters that should be included? We could instead pass a config file with a bunch
	of required fields: type of statistical distribution to follow, number of traces, anomaly distributions, etc.

"""
import random
import igraph
import sys
import math

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
	to guarantee that a recusrive search down the AND-branches recombine at some node, which can then be found by chopping off
	the non-matching prefixes of these searches. For example, the left and right searches for (ABC&EFG)H gives "ABCH..." and "EFGH...". 
	Given the constraints, the joining node of the AND is H, and can be detected as such, as the first matching char in the left and right strings.
	
	Returns: A string of the concatenated chars of each node visited. The string is appended with ",+1" for anomalous traces, ",-1" for non-anomalous traces.
	Also returns a list of nodes, where the index for each node corresponds with its index in the concatenated char string.
	
	Returns: A list of (src,dest) igraph-edge pairs, representing all transitions for this trace. Th reason for this construction is we need to preserve some of the
	edge info for post-processing analysis, but primarily because AND splits (parallel paths) can't be represented as a string.
	
	TODO: This may need to be simplified with BFS queue or stack-based implementation.
	"""
	def _generateTrace(self,startNode):
		curNode = startNode
		isAnomalousTrace = False
		transitionList = []
		
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
						break
				if not loopEdge["isTraversed"]:
					loopEdge["isTraversed"] = True #mark the loop edge as traversed; this is only required on loop edges, to prevent endless recursion
					pLoop = float(loopEdge["probability"])
					r = float(random.randint(1,100)) / 100.0
					if r <= pLoop:
						transitionList.append(loopEdge)
						curNode = self._graph.vs[loopEdge.target]
						loopTaken = True
			#continue
			
			if not loopTaken:
				#after loops, outgoing edges are exclusively AND or OR or SEQ
				if "AND" in edgeTypes:
					outEdges = [edge for edge in outEdges if edge["type"] == "AND"]
					if len(outEdges) < 2:
						print("ERROR out edges for split node < 2: "+str(outEdges)+" model: "+self._model)
						raw_input()
					#For AND splits, go down both branches, then glue their shared prefixes to get the re-join point of the branches
					leftNode = self._graph.vs[outEdges[0].target]
					leftPath = self._generateTrace(leftNode)
					rightNode = self._graph.vs[outEdges[1].target]
					rightPath = self._generateTrace(rightNode)
					#print(str(rightPath))
					#MAKE THIS A FUNCTION
					#make sure this whole search returns index of END node if no match is found; although, we do guarantee each AND split is appended with an alpha
					#find the first char at which the two strings match; this is the node (via its name/label) at which the AND rejoined
					i = 0
					matchFound = False
					#for each char in leftPath, search for match in rightPath
					while i < len(leftPath) and not matchFound:
						j = 0
						while j < len(rightPath) and not matchFound:
							#print("LEFT: "+str(leftPath))
							#print "Left: "+str(leftPath[i])
							#print "Right: "+str(rightPath[j])
							#print("RIGHT: "+str(rightPath))
							if self._getNode(leftPath[i].source)["label"] == self._getNode(rightPath[j].source)["label"]:
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
					curNode = self._graph.vs[leftPath[leftJoinIndex].source]
					
					#this should be unreachable, since every AND is appended with some char. Should never reach END node.
					if not matchFound:
						print("ERROR not matchFound in _generate() for AND. "+str(matchFound)+"  node: "+curNode["label"])
				
				#OR split detected, so stochastically choose an edge to follow
				elif "OR" in edgeTypes:
					outEdges = [edge for edge in outEdges if edge["type"] == "OR"]
					r = float(random.randint(1,100)) / 100.0 #generates a random float in range 0.01-1.00
					pLeft = float(outEdges[0]["probability"])
					pRight = float(outEdges[1]["probability"])
					#detect and notify if probability labels are indeed valid probs; that is, they sum to 1.0, within a tolerance of 0.01
					if math.fabs((pLeft + pRight) - 1.0) > 0.01:
						print("In OR WARNING possibly invalid probabilities detected. Edge probabilities do not sum to 1.0: "+str(pLeft)+" "+str(pRight)+"    Node: "+curNode["label"])

					#select an edge at random, according to the probability labels of each edge. Selection is uniform-random for now.
					if r < pLeft: #Let pLeft, pRight fill the region from 0.0-1.0. If r in pLeft (the lower portion of the interval), choose left; else choose right
						transitionList.append(outEdges[0])
						curNode = self._graph.vs[outEdges[0].target]
					else:
						transitionList.append(outEdges[1])
						curNode = self._graph.vs[outEdges[1].target]
				
				#lastly, only one option left: current node has only one outgoing "SEQ edge"
				elif "SEQ" in edgeTypes:
					outEdges = [edge for edge in outEdges if edge["type"] == "SEQ"]
					#detect and notify of more than one SEQ out-edge for a particular node, which is an invalid topology
					if len(outEdges) > 1:
						print("WARNING more than one SEQ edge in _generateTrace(). Num edges: "+str(outEdges))
					transitionList.append(outEdges[0])
					curNode = self._graph.vs[outEdges[0].target]
				else:
					#this else should be unreachable, so notify if not
					print("ERROR unreachable else reached in _generateTrace() for edgeTypes: "+str(edgeTypes))
					transitionList.append(outEdges[0])
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
	empty transition to only (A,B), from (A,^_123) and (^_123, B)
	
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
							print("WARN contiguous empty branch encountered in _postProcessEdges() of DataGenerator, unhandled")		
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
	Just calls the inner recursive driver, then does some basic cleanup and postprocessing on the returned list of edges.
	
	Returns: List of edge-label tuples representing all source-dest transitions: [(A,B), (B,C) ... ]
	def GenerateTrace(self):
		edges = self._generate(self._startNode)
		edges = self._postProcessEges(edges)
		edgeLabels = [(edge.source["label"],edge.target["label"])]
	"""

	"""
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
		
	@trace: an unordered list of igraph-edges
	@ofile: the output file handle
	"""
	def _writeTrace(self,trace,ofile):
		hasAnomaly = False
		ostr = ""
		for e in trace:
			if e["isAnomalous"]:
				hasAnomaly = True
	
		"""	#outputs a simple edge format
		if hasAnomaly:
			ostr += "+\n" #print a plus to indicate an anomalous trace
		else:
			ostr += "-\n"

		for edge in trace:
			ofile.write(self._getNode(edge.source)["label"]+"\t"+self._getNode(edge.target)["label"]+"\n")
		ofile.write("\n")
		"""
		
		if hasAnomaly:
			ostr += "XP\n"
		else:
			ostr += "XN\n"
			
		#vertex declarations; here I preserve the igraph vertex id's a the .g indices
		vertexDict = {}
		for edge in trace:
			if edge.source not in vertexDict:
				vertexDict[edge.source] = self._getNode(edge.source)["label"]
			if edge.target not in vertexDict:
				vertexDict[edge.target] = self._getNode(edge.target)["label"]
		for k in vertexDict.iterkeys():
			ostr += ("v "+str(k)+" "+vertexDict[k]+"\n")
			
		#output the edges
		for edge in trace:
			ostr += ("d "+str(edge.source)+" "+str(edge.target)+"\n")
		ostr += "\n"
		
		ofile.write(ostr)
		
	"""
	Once a trace has been generated, this resets the state of the generator so it is ready to generate a new trace.
	"""
	def _reset(self):
		self._graph.es["isTraversed"] = False #in igraph, this assignmnet is applied to all edges
		
	"""
	Main driver for generating traces.
	"""
	def GenerateTraces(self, graphmlPath, n, outputFile="traces.txt"):
		if not graphmlPath.endswith(".graphml"):
			print("ERROR graphml path is not a graphml file. Path must end with '.graphml'.")
			return
	
		print("Generating traces...")
		ofile = open(outputFile, "w+")
		self._buildGraph(graphmlPath)
		i = 0
		while i < n:
			trace = self._generateTrace(self._startNode)
			self._writeTrace(trace,ofile)
			self._reset()
			i += 1
		print("Trace generation completed and output to "+outputFile+".")
		ofile.close()

def usage():
	print("python ./DataGenerator -file=(path to graphml file) -n=500 [-ofile=(path to output file; defaults to traces.txt if not passed)]")


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
		
	ofile = "traces.txt"
	if "-ofile=" in sys.argv[3]:
		ofile = sys.argv[3].split("=")[1]

	generator = DataGenerator()
	generator.GenerateTraces(graphFile, n, ofile)

if __name__ == "__main__":
	main()


