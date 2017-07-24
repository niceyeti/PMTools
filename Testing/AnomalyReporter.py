"""
Given the output of gbad containing found-anomalies, and the original trace log containing
+/- anomaly labelings, this object compares the two and generates the matrix for
true positives, false positives, true negatives, and false negatives.

The gbad output may contain output of any gbad version (mdl, mps, prob), and output of each gbad
version can be concatenated into a single file as input to this script. Mdl and mps output is the same,
but the fsm version declares anomalies slightly differently. All are plaintext files, which ought to be
updated to something more rigorous. This doesn't handle fsm output directly, but can with a little
preprocessing: grep "transaction containing anomalous structure" $fsmResult | uniq | sort > $fsmTemp

The info is just printed to the output, but keep it parseable if possible.
"""
from __future__ import print_function
import sys
from Dendrogram import *
import igraph
import math

class AnomalyReporter(object):
	def __init__(self, gbadPath, logPath, resultPath, markovPath, dendrogramPath=None, dendrogramThreshold=0.05, traceGraphPath="../SyntheticData/traceGraphs.py"):
		self._gbadPath = gbadPath
		self._logPath = logPath
		logFile = open(self._logPath, "r")
		self._parseLogAnomalies(logFile)
		self._numTraces = len(self._logTraces)
		
		self._resultPath = resultPath
		self._dendrogramPath = dendrogramPath
		self._dendrogramThreshold = dendrogramThreshold
		self._markovModel = self._readMarkovModel(markovPath)
		#calculate and store the markovian-based trace count; this is used to calculate edge probabilities based on trace counts
		self._traceCount = 0.0
		for edgeKey in self._markovModel:
			if edgeKey[0].upper() == "START":
				self._traceCount += self._markovModel[edgeKey]

		#read in the trace subgraphs (all traces in graph form, given by the mined model)
		self._traceGraphs = self._readTraceGraphs(traceGraphPath)
				
	"""
	Reads the trace-subgraph file of graph representations of each trace, for which the file is formatted as
	tuples of (traceNo, [edgeList like ... ('a','s'), ('s','d'), ('g','s')])
	"""
	def _readTraceGraphs(self, traceGraphPath):
		traceGraphDict = {} #dictionary of trace graphs, 
		
		with open(traceGraphPath,"r") as tf:
			for line in tf.readlines():
				tup = eval(line.strip())
				traceNo = tup[0]
				traceGraph = tup[1]
				if traceNo in traceGraphDict.keys():
					print("ERROR traceNo already in trageGraph in _readTraceGraphs")
				traceGraphDict[traceNo] = traceGraph
		
		return traceGraphDict

	"""
	Expected file format is a single line containing the tring version of the markov model,
	a python dictionary of keys consisting of concatenated src-dst vertex names, and values
	representing the edge transition counts.
	"""
	def _readMarkovModel(self, markovPath):
		f = open(markovPath, "r")
		s = f.read().strip()
		f.close()

		return eval(s)
	
	"""
	Given a file containing gad output, parses the text for all of the anomalies detected. Each
	anomaly must contain the corresponding trace number associated with a trace in the original
	log file (labelled +/- for anomaly status).
	
	Returns: A list of integers that are the ids of any 
	"""
	def _parseGbadAnomalies(self, gbadFile):
		self._detectedAnomalyIds = []
		gbadOutput = gbadFile.readlines()
		#print("output: "+gbadOutput)
		gbadFile.close()

		"""
		Gbad output (in the versions I've used) always has anomalies anchored with the file-unique string
		"from example xx" where xx is the integer number of the anomalous graph, the same as the trace id in the trace log.
		Thus, search for all lines with this string, parse the number, and we've a list of trace-ids for the anomalies.
		"""
		for line in gbadOutput:
			#detects gbad-mdl, -mps, -prob anomal declarations (mdl/mps use "from example", gbad-prob uses "from positive example")
			if "from example " in line:
					#print("found anom: "+line)
					#parses 50 from 'from example 50:'
					id = int(line.strip().split("from example ")[1].replace(":",""))
					self._detectedAnomalyIds.append(id)
			#detects gbad-prob anomalous subgraph example declarations
			if "in original example " in line:
					#print("found anom: "+line)
					#parses 50 from 'in original example 50)'
					id = int(line.strip().split("in original example ")[1].replace(")",""))
					self._detectedAnomalyIds.append(id)

			#detects output format of gbad-fsm
			if "transaction containing anomalous structure:" in line:
				id = int(line.split("structure:")[1].strip())
				self._detectedAnomalyIds.append(id)
				
	"""
	Parses a trace log file into the object's internal storage. These are the ground truth anomalies, not those detected by gbad.
	
	@self._anomalies: a list of anomalous traces (tokenized by comma)
	"""
	def _parseLogAnomalies(self,logFile):
		#maintain traces internally as a list of <traceNo,+/-,trace> string 3-ples
		self._logTraces = [trace.split(",") for trace in logFile.readlines() if len(trace.strip()) > 0]
		#get the subset of the traces which are anomalies
		self._logAnomalies = [trace for trace in self._logTraces if trace[1] == "+"]
		#get the non-anomalies
		self._logNegatives = [trace for trace in self._logTraces if trace[1] == "-"]
		logFile.close()
		
	"""
	Given a float in range 0.0 to 1.0, such as 0.4567532, returns "45.67%" (hundredths precision)
	"""
	def _floatToPctStr(self, f):
		return str(float(int(f * 10000)) / 100.0)+"%"

	"""
	Keep this clean and easy to parse.
	"""
	def _displayResults(self):	
		output = "Statistics for log parsed from "+self._logPath+", anomalies detected\n"
		#output += "True positives:  \t"+str(len(self._truePositives))+"\t"+str(self._truePositives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "False positives:  \t"+str(len(self._falsePositives))+"\t"+str(self._falsePositives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "True negatives: \t"+str(len(self._trueNegatives))+"\t"+str(self._trueNegatives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"
		#output += "False negatives: \t"+str(len(self._falseNegatives))+"\t"+str(self._falseNegatives).replace("set(","{").replace("{{","{").replace(")","}}").replace("}}","}")+"\n"

		output += ("Num traces (N): \t"+str(self._numTraces)+"\n")
		output += ("Accuracy:          \t"+str(self._accuracy)+"  ("+self._floatToPctStr(self._accuracy)+")\n")
		output += ("Error rate:         \t"+str(self._errorRate)+"  ("+self._floatToPctStr(self._errorRate)+")\n")
		output += ("Recall:              \t"+str(self._recall)+"  ("+self._floatToPctStr(self._recall)+")\n")
		output += ("Precision:          \t"+str(self._precision)+"  ("+self._floatToPctStr(self._precision)+")\n")
		
		output += ("True positives:   \t"+str(len(self._truePositives))+"\t"+str(self._truePositives)+"\n")
		output += ("False positives:  \t"+str(len(self._falsePositives))+"\t"+str(self._falsePositives)+"\n") 
		output += ("True negatives: \t"+str(len(self._trueNegatives))+"\t"+str(self._trueNegatives)+"\n")
		output += ("False negatives: \t"+str(len(self._falseNegatives))+"\t"+str(self._falseNegatives)+"\n")

		print(output)
		
		ofile = open(self._resultPath, "w+")
		ofile.write(output)
		ofile.close()

	"""
	Gbad doesn't always report all instances of a given anomaly; so if "ABC" is reported as an 
	anomaly, it doesn't always report all "ABC" traces as anomalies in it results. 
	
	NOTE: I've only currently written this to look for traces (strings) in the trace file which are
	matching strings. This covers 99% of the cases, however, traces like "ACB" could theoretically
	be included and NOT caught as equivalent to some found-anomaly "ABC". THIS NEEDS TO BE FIXED.
	That is, for each anomaly, we need to reconstruct it graphically according to the mined model, then compare 
	the anomaly to all other traces as graphs.
	
	@anoms: list of anomalies as a list of 3-ples: string-id (the first field of each trace in logTraces), +/-, and traceStr
	
	returns: Full list of anomalous traces as 3-ples.
	"""
	def _unifyAnomalies(self):
		#print("detected: "+str(set(self._detectedAnomalyIds)))
		#print("traces: "+str(self._logTraces))
		anoms = []
		#get the anomaly list as a list of 3-ples
		for id in set(self._detectedAnomalyIds):
			for trace in self._logTraces:
				if trace[0] == str(id):
					anoms.append(trace)
	
		ids = set([a[0] for a in anoms])
		equivalentAnoms = []
		#given each anomaly, look for others with the same trace-string which are not yet included in the anomaly set
		for anom in anoms:
			id = anom[0]
			traceStr = anom[2]
			#search for other log-traces with this same trace-string. This is an insufficient match, since these are technically graphs.
			for logTrace in self._logTraces:
				#if logTrace[2] == traceStr:
				#	print("traceStr hit"+str(logTrace))#+"  ids: "+str(ids))
				if logTrace[2] == traceStr and logTrace[0] not in ids:
					#print("Extra anomaly detected for "+traceStr+" "+id+": "+logTrace[0])
					equivalentAnoms.append(logTrace)
					ids.add(logTrace[0])
		
		anoms += equivalentAnoms
					
		#print("all anoms: "+str(anoms))
		return anoms
		
	"""
	TODO: Dendrogram could certainly be its own class at some point; this is fine for now.
	
	A dendrogram is as demonstrated in dendrogram.txt. The intent is for the Dendrogram object
	to support querying, such as "given this anomalous/outlier trace, what is the nearest compressing substructure?"
	
	returns: The dendrogram, which is just an ordered list of compression levels, with the last/bottom-most at back
	"""
	def _buildDendrogram(self, path):
		anomalyIds = []
		dendrogram = []
		f = open(self._dendrogramPath,"r")
		
		#build the compression levels, each of which is an object with compressed id's, max compressed id's, compression factor (from gbad), num instances, etc
		for line in f.readlines():
			if len(line.strip()) > 0:
				cl = CompressionLevel(line.strip())
				dendrogram.append(cl)
		
		#create the edge distributions from the trace subgraph file
		for level in range(len(dendrogram)):
			sub = dendrogram[level]
			sub.EdgeDist = self._buildSubstructureEdgeDist(dendrogram, level)
		
		return dendrogram

	#Builds the edge distribution for a given substructure in a-priori fashion, using the trace graphs populated prior.
	#NOTE: this requires self._traceGraphs was populated before
	def _buildSubstructureEdgeDist(self, dendrogram, level):
		sub = dendrogram[level]
		#populate the first level / root-ids for this substructure in the dendrogram; these are used to pull the original traces from the tracegraph file
		rootIds = self._getSubTraceIds(dendrogram, level)
		sub.Attrib["RootIds"] = rootIds
		
		#build the edge distribution for this substructure
		edgeDist = {}
		for rootId in rootIds:
			#count edges connected to this substructure (one vertex in and one out for a given edge, undirected)
			traceEdges = self._traceGraphs[int(rootId)]
			for edge in traceEdges:
				if (edge[0] in sub.SubGraphVertices and edge[1] not in sub.SubGraphVertices) or (edge[1] in sub.SubGraphVertices and edge[0] not in sub.SubGraphVertices):
					if edge in edgeDist.keys():
						edgeDist[edge] += 1
					else:
						edgeDist[edge] = 1
		
		return edgeDist
		
	"""
	A recursive search procedure for retrieving a child of a level (substructure) in the dendrogram.
	
	In some level Li for substructure Si, there is some compressed id ID. We wish to find the next child
	sub into which it is further mapped into some compressing substructure further below.
	BEWARE that if the dendrogram does not represent a fully compressed log, this method will bottom out early for traces which
	did not reach full compression.
	
	@level: The integer index of the level within which to check for this id
	@id: An active id in @level
	
	Returns: Integer index of this nodes next compressing substructure in the dendrogram
	"""
	def _getChild(self, dendrogram, level, id):
		#one base case: if id == -1, this is the most compressing sub
		if id == "-1":
			return level - 1
			
		if level >= len(dendrogram):
			print("ERROR: no child found for id/level: "+str(id)+"/"+str(level)+".  This can occur if --recurse parameter set too low, and further compression could have had with more iterations.")
			return level - 1
			
		if id in dendrogram[level].CompressedIds:
			return level
		#recurse
		return self._getChild(dendrogram, level+1, dendrogram[level].IdMap[id])

	"""
	Given the dendrogram, returns a list of (dict,string) tuples with the dict characterizing the frequency distribution of
	each non-terminal level's children, and the string is the substructure name. The index of each dictionary corresponds with the level in the
	dendrogram. 
		[({"SUB_1":3, "SELF":4},"NAME OF THIS NODE"),({...},"NAME NODE")]
		
	Note that frequently some nodes at a specific level will reach max compression; these are treated as "children"
	of this substructure/level, which is valid since some others compressed by this level will not be maximally compressed but are
	nonetheless siblings.
	
	Also note that this may occasionally output a disconnected set of substructures, most often for the "SUB_init" for substructure compressed. This is
	correct, and results when the first substructure compressed consists of only maximally-compressed traces, looping it to itself, but giving it no children.
	
	Returns: freqDist, a list of dictionaries GUARANTEED to be ordered by lines in the dendrogram file, and hence by compression order and topological order.
	"""
	def _getDendrogramDistribution(self,dendrogram):
		dictList = []

		"""
		print("DENDROGRAM: ")
		for record in dendrogram:
			print(str(record))
		print("END")
        """
		
		for level in range(len(dendrogram)):
			freqDist = {}
			cl = dendrogram[level]
			#check if level has maximally compressed some subs; otherwise this level doesn't have any of its elements as its own children
			if len(cl.MaxCompressedIds) > 0:
				freqDist = {cl.SubName:len(cl.MaxCompressedIds)}
			#get immediate child substructures of this level: look across all ids mapped in all lower layers for next compressing substructure
			for id in cl.CompressedIds:
				if id not in cl.MaxCompressedIds: #see above: already accounted for child/max compressed id's
					childLevel = self._getChild(dendrogram, level+1, cl.IdMap[id])
					#print("childLevel: "+str(childLevel))
					childName = dendrogram[childLevel].SubName #some information stuffing, to identify the reflexive loops of nodes
					if childName not in freqDist.keys():
						freqDist[childName] = 1
					else:
						freqDist[childName] += 1
			print("FreqDist, level "+str(level)+" sub "+cl.SubName+": "+str(freqDist))
			dictList.append((freqDist,cl.SubName))

		return dictList

	"""
	Utility for converting a freqDictList (per _getDendrogramDistribution) to an igraph object, for plotting and analysis.
	The nodes are connected according to the relationships given by @freqDictList, and the edges store the frequencies in their
	"weight" attribute, for analyses.
	
	Returns: igraph object description of the freqDictList
	"""
	def _getFreqDistGraph(self, freqDictList):
		#build the edge list locally
		es = []
		rootName = freqDictList[0][1]
		print("ROOT: "+rootName)
		for fd in freqDictList:
			nodeName = fd[1]
			#add the edges for this layer to all lower ones, with their frequency/weight
			for key in fd[0].keys():
				es.append((nodeName,key,fd[0][key]))
		#es populate, now use it to build set of unique vertex names
		vs = set()
		for edge in es:
			vs.add(edge[0])
			vs.add(edge[1])
		#print("VS: "+str(vs))
		g = igraph.Graph(directed=True)
		g.add_vertices(list(vs))
		edgeList = [(edge[0],edge[1]) for edge in es]
		edgeWeights = [edge[2] for edge in es]
		g.add_edges(edgeList)
		g.es["weight"] = edgeWeights
		g.es["label"] = [str(weight) for weight in edgeWeights]
		
		for v in g.vs:
			v["label"] = v["name"]
			if v["name"] == rootName:
				rootId = v.index

		#calculate the pagerank values; this is reverse pagerank, since the parent subs point to their child substructures
		g.vs["reversePagerank"] = g.pagerank()
		#print em (this is just for viewing, as it doesn't connect the values to traces)
		rpr = sorted([(v["name"],v["reversePagerank"]) for v in g.vs], key=lambda t: t[1])
		print("Reverse pagerank values: ")
		for tup in rpr:
			print("\t"+str(tup))
		print("end")
		
		return g
		
	"""
	@freqDictList: A list of frequency distribution dictionaries  per _getDendrogramDistribution
	
	Returns: Igraph description of frequency distribution.
	"""
	def _visualizeDendrogram(self, freqDictList):
		g = self._getFreqDistGraph(freqDictList)

		#layout = igraph.Graph.layout_reingold_tilford(mode="out",root=rootId)
		layout = g.layout("sugiyama")
		#layout = g.layout_sugiyama()
		#layout = g.layout_reingold_tilford(mode="in", root=[rootId])
		outputPlot = igraph.plot(g, layout = layout, bbox = (1000,1000), vertex_size=50, vertex_label_size=15)
		outputPlot.save("dendrogram.png")
		#igraph.plot(g, bbox = (1000,1000), vertex_size=50, vertex_label_size=15)
		#layout = graph.layout("reingold")
		#igraph.plot(g,layout = layout.reingold.tilford(g, root = rootName))
		g.write_graphml("dendrogram.graphml")
		
		return g
		
	"""
	An experiment to see if entropy metrics distinguish anomalies/noise: score each substructure according to the
	distribution of substructures in all of its ancestors, by including and excluding this substructures ancestors.
	
	NOTE: This sums over all ancestors in which a particular substructure appears, so its entropy may be a sum over multiple distributions.
	
	@dendrogram: The dendrogram, as a list of DendrogramLevel objects.
	@freqDist: The frequency distribution of the denddrogram levels, as a list of tuples: [({'SUB6': 1, 'SUB1': 8, 'SUB0': 139, 'SUB3': 1}, 'SUB_init'), ... ]
	
	Returns: Mapping of substructure names (freqDist keys) to sum entropy values over all ancestors.
	"""
	def _getSubstructureEntropyMap(self, dendrogram, freqDist):
		subMap = {}
		i = len(freqDist) - 1
		while i >= 0:
			levelName = freqDist[i][1]
			sumEnt = 0.0
			j = i - 1
			while j >= 0:
				#calculate the difference in entropy with and without this substructure in the current distribution
				if levelName in freqDist[j][0].keys():
					#calculate entropy with this substructure
					sumX = float(sum(freqDist[j][0].values()))
					entWithSub = -sum([float(val)/sumX * math.log(float(val)/sumX, 2.0) for val in freqDist[j][0].values()])
					#print("ent1: "+str(entWithSub))
					#calculate entropy without this substructure
					sumX = float(sum([item[1] for item in freqDist[j][0].items() if item[0] != levelName]))
					entSansSub = -sum([float(item[1])/sumX * math.log(float(item[1])/sumX,2.0) for item in freqDist[j][0].items() if item[0] != levelName])
					#print("ent2: "+str(entSansSub))
					sumEnt += (entWithSub - entSansSub)
					#subMap[levelName] = ent
				j -= 1
			subMap[levelName] = sumEnt
			i -= 1

		return subMap

	"""
	Given the sub-ent-map, we can also examine the cumulative entropy of a substructures ancestors.
	This may be useful, may be not, but is worth looking at.
	
	@freqDist: Used to look up all paths from this substructure to the root
	@subEntMap: mapping from substructure names to their associated sum entropy over all parent distributions in which they occur.
	"""
	def _getCumulativeSubstructureEntropyMap(self, freqDist, subEntMap):
		cumEntMap = {}
		i = len(freqDist) - 1
		#walk up, using the subEntMap to map all of a substructure's ancestors to their entropy values
		while i >= 0:
			subName = freqDist[i][1]
			#build the ancestor set for this node
			ancestorQ = [subName]
			ancestors = set()
			ancestors.add(subName)
			while len(ancestorQ) > 0: #bfs search for ancestors
				subName = ancestorQ[0]
				ancestors.add(subName)
				#print("sub: "+subName)
				j = i - 1
				#walk up, finding all predecessors of this substructure name
				while j >= 0:
					if subName in freqDist[j][0].keys():
						predName = freqDist[j][1]
						if predName not in ancestors:
							ancestorQ.append(predName)
						ancestors.add(predName)
					j -= 1
				#pop the processed front node
				ancestorQ = ancestorQ[1:]
				#print("q>> "+str(ancestorQ))
				#print("ancs: "+str(ancestors))

			#print("Ancestors: "+str(ancestors))
			entSum = 0.0
			for ancestor in ancestors:
				entSum += subEntMap[ancestor]
			cumEntMap[freqDist[i][1]] = entSum

			i -= 1
			
		print("Cumulative Entropies: "+str(cumEntMap))

		return cumEntMap

	"""
	Convenience wrapper of _getSubTraceIds using a name parameter instead.
	
	@subName: substructure name in dendrogram whose ids we want
	"""
	def _getSubTraceIdsByName(self, dendrogram, subName):
		index = -1
		ids = []
		
		for level in range(len(dendrogram)):
			if subName.lower() == dendrogram[level].SubName.lower():
				index = level
				break
				
		if index == -1:
			print("ERROR in _getSubTraceIdsByName: index not found for sub name: "+subName)
		else:
			ids = self._getSubTraceIds(dendrogram, index)
		
		return ids
		
	"""
	Given an index in the dendrogram representing a substructure, recovers the original trace ids of those id's compressed
	by that sub. Note ought to be part of a Dendrogram api.
	
	Returns: original id list of all compressed ids for the substructure given by @subIndex.
	"""
	def _getSubTraceIds(self, dendrogram, subIndex):
		ids = dendrogram[subIndex].CompressedIds
		i = subIndex - 1
		while i >= 0:
			ids = [dendrogram[i].ReverseIdMap[id] for id in ids]
			i -= 1
		
		return ids

	"""
	Analyzes the edge/node and other distribution measures comparing the 
	child substructures with various distributions of the overall graph. 
	
	The general approach is simply to compare the distribution of edges/nodes/substructures with the distribution
	given by the overall graph. This provides a potential measure of things seeming unusual (divergent) in the context of a pattern.
	
	Currently this is not well-defined, for a range of reasons: reflexive connections (include these in dists or not?), disconnected
	graphs (a frequent case) yielding zero edge/markovian probability connecting substructures, etc. The biggest flaw in this
	method is simply that it lacks an objective; however, the framework seems highly useful, however distributions and analytics
	are defined.
	
	Method: Given a dendrogram, proceed top down, analyzing divergence of each child wrt the distribution of the overall graph
	given by self._markovModel. 
	
	Returns: A dict of dicts. The key in the outer dict is a particular substructure. Within this dict, the keys are the names of its children (which may
	include itself), and the values are another dict of attributes for that child substructure

	"""
	def _analyzeChildSubDistributions(self, dendrogram):
		childDivergenceMap = {}
	
		#friendly verification reminder
		print("Running child sub distribution analysis with traceCount="+str(self._traceCount))
		print("Note that child sub distribution analysis has not been evaluated nor defined (many distributions could be defined)")
		
		#get the distribution of children under each level
		childDists = self._getDendrogramDistribution(dendrogram)
	
		#analyze each level's child distribution wrt the edge distribution of the overall graph
		for i in range(0,len(childDists)):
			dist = childDists[i]  #returns distributions as : [({"SUB_1":3, "SELF":4},"NAME OF THIS NODE"),({...},"NAME OF NEXT NODE")]
			parentName = dist[1]
			parentLevel = self._getDendrogramLevelByName(dendrogram, dist[1])
			freqDist = dist[0]
			
			#sum the frequencies of all children (normalization factor)
			z = 0.0
			#calculate divergence between connections to child and connections in the overall graph
			for childName in freqDist:
				if childName != parentName:
					z += freqDist[childName]
			
			#calculate divergence between connections to child and connections in the overall graph
			for childName in freqDist:
				#exclude self from analysis; this is done because we're always analyzing wrt children; all nodes will be compressed eventually, and will have a value from their parent
				if childName != parentName:
					child = self._getDendrogramLevelByName(dendrogram, childName)
					childFrequency = freqDist[childName]
					childConnectingEdgeProb = float(childFrequency) / float(z)
					#get the uniq edges connecting substructures and compare with overall graph distribution
					edges = self._getConnectingEdges(parentLevel.SubGraphVertices, child.SubGraphVertices, self._markovModel)
					graphConnectingEdgeProb = self._getMarkovianEdgeProb(edges)
					#add properties to dendrogram level itself; as lists, since one substructure may be the child of multiple parents
					if "ChildLocalConnectivityProbabilities" not in child.Attrib or child.Attrib["ChildLocalConnectivityProbabilities"] == 0:
						child.Attrib["ChildLocalConnectivityProbabilities"] = [childConnectingEdgeProb]
					else:
						child.Attrib["ChildLocalConnectivityProbabilities"].append(childConnectingEdgeProb)
					if "GlobalConnectivityProbabilities" not in child.Attrib or child.Attrib["GlobalConnectivityProbabilities"] == 0:
						child.Attrib["GlobalConnectivityProbabilities"] = [graphConnectingEdgeProb]
					else:
						child.Attrib["GlobalConnectivityProbabilities"].append(graphConnectingEdgeProb)

					#TODO: Could also evaluate sum vertex/edge probability of the complete substructure, given the graph
		
					if child.SubName in childDivergenceMap.keys():
						childDivergenceMap[child.SubName].append((childConnectingEdgeProb, graphConnectingEdgeProb))
					else:
						childDivergenceMap[child.SubName] = [(childConnectingEdgeProb, graphConnectingEdgeProb)]
					
		return childDivergenceMap				

	"""
	Measures the edge divergence of edges connecting to a substructure wrt the edge distribution in the overall graph. 
	This is a metric of "in the context of a normative pattern, something unusual occurs" in the sense that we are looking for divergence
	between the frequency of edges in this context vs. its frequency in the complete graph. The assumption being that the
	recursive compression process places unusual behavior in the edges connecting substructures and at the leaves.
	
	The divergence metric is KL: Sum[ P(x)*log(P(x)/Q(x)) ] where P(x) is global probability of edge, and Q(x) is probability of edge in this substructure context.
	The values are stored in the dendrogram "EDGE_KL_PQ" and "EDGE_KL_QP" attributes, where P is described in previous line, Q is Sum[ Q(x)*log(Q(x)/P(x)) ]
	
	This returns nothing; the information is printed and also stored in each dendrogram level as described.
	
	NOTE: This could also incorporate node probabilities, but that depends on the variance of node occurrences throughout the graph, which is sort of zero
	for the process model definition (eg, a node can only occur in one position, hence its global/local probability will be the same).
	"""
	def _analyzeEdgeConnectivityDivergence(self, dendrogram):
		
		for level in dendrogram:
			#calculate divergence
			if len(level.EdgeDist.keys()) > 0:
				divPQ = 0.0
				divQP = 0.0
				
				#get normalization constant for all global edge probs; required to make global probs a proper probability distribution wrt the local edge probs
				#zNormGlobal = 0.0
				#for key in level.EdgeDist.keys():
				#	zNormGlobal += self._markovModel[key]
				
				#keys are tuples of node names: ('c','b')
				for key in level.EdgeDist.keys():
					#get the edge probability in context of this substructure
					pLocal = float(level.EdgeDist[key]) / float(level.NumInstances)
					#pLocal = float(level.EdgeDist[key]) / float(sum(level.EdgeDist.values())) 
					pLocal = max(0.0001, min(0.9999,pLocal)) #clamp probs to range [0.001-0.999] to prevent zero/one problems in KL calculations

					#get the global edge probability; checking first for markov-model and edge-dist consistency
					if key not in self._markovModel.keys():
						print("\n\n>>> ERROR: local edge from dendrogram not in markovModel in _analyzeEdgeConnectivityDivergence")
						print("MARKOV: "+str(self._markovModel))
						print("Edge dist: "+str(level.EdgeDist))

					#pGlobal = float(self._markovModel[key]) / float(zNormGlobal)  #the characterization of p(edge) over the number of traces
					pGlobal = float(self._markovModel[key]) / float(self._numTraces)
					pGlobal = max(0.0001, min(0.9999,pGlobal))
					#pGlobal = float(self._markovModel[key]) / float(self._numTraces) #the characterization of p(edge) over the number of traces

					#check for math errors
					if pLocal == 0 or pGlobal == 0:
						print("ERROR pLocal or pGlobal zero in _analyzeEdgeConnectivityDivergence: pLocal="+str(pLocal)+"  pGlobal="+str(pGlobal))

					#print(str(pGlobal)+"   "+str(pLocal))
					
					##accumulate divergence of QP and PQ
					#divPQ += pLocal * math.log(pLocal / pGlobal)
					#divQP += pGlobal * math.log(pGlobal / pLocal)					
					
					#binomial edge construction
					pNotLocal = 1.0 - pLocal
					pNotGlobal = 1.0 - pGlobal
					#accumulate divergence of PQ
					#print("pNotGlob: "+str(pNotGlobal)+"  pGlob: "+str(pGlobal))
					#print("pNotLocal: "+str(pNotLocal)+"  pLoc: "+str(pLocal))
					divPQ += (pLocal * math.log(pLocal / pGlobal) + pNotLocal * math.log(pNotLocal / pNotGlobal))
					#accumulate divergence of QP
					divQP += (pGlobal * math.log(pGlobal / pLocal) + pNotGlobal * math.log(pNotGlobal / pNotLocal))
					
				level.Attrib["EDGE_KL_PQ"] = divPQ
				level.Attrib["EDGE_KL_QP"] = divQP
				
			else:
				#empty edge distributions are okay: they occur often when a subtructure is maximally compressed
				level.Attrib["EDGE_KL_QP"] = -999
				level.Attrib["EDGE_KL_PQ"] = -999

		#print the KL divergence values for each substructure
		print("KL divergence values per level")
		for level in dendrogram:
			print(level.SubName+"    pq: "+str(level.Attrib["EDGE_KL_PQ"])+"    qp: "+str(level.Attrib["EDGE_KL_PQ"]))

		
	"""
	Gets the TRACE-probability of an edge, which is defined as the count of that edge divided
	by the number of traces. The number of traces is necessarily contained by the sum over
	edge-counts for edges starting with 'START' node.
	
	NOTE: This requires self._traceCount was set in markov-model init
	
	@edges: a list of edge tuples as ('a','b')
	"""
	def _getMarkovianEdgeProb(self, edges):
		edgeCount = 0.0
		
		for edge in edges:
			edgeCount += self._markovModel[edge]
				
		if self._traceCount == 0: #sanity check
			print("ERROR div-zero in _GetMarkovianEdgeProb, hosed...")
				
		return float(edgeCount) / float(self._traceCount)

	"""
	TODO: This is very dangerous, since it assumes any link between the two vertex sets is an edge connecting the substructures.
	If metrics confirm this method is useful, then this needs to be re-written to get the edges directly, by storing them during the compression process.
	
	Method: given sv1 and sv2, two sets of vertices by name str's, gets all the edges connecting them via the passed markovModel, a list of edge-frequency tuples.	
	
	Returns: all edges in the passed markovian model, for which src/dest node are in complementary sets sv1 or sv2. In short, returns all edges in either direction, 
	connecting sv1 to sv2 or sv2 to sv1.
	"""
	def _getConnectingEdges(self, sv1, sv2, markovModel):
		connectingEdges = []

		for v1 in sv1:
			for v2 in sv2:
				for edge in markovModel:
					#check first direction
					if edge[0] == v1 and edge[1] == v2:
						connectingEdges.append(edge)
					#check opposite direction
					if edge[1] == v1 and edge[0] == v2:
						connectingEdges.append(edge)
		
		if len(connectingEdges) == 0:
			print("WARNING no connecting edges found via markov model for "+str(sv1)+"  AND  "+str(sv2))

		return connectingEdges


	#returns dendrogram object by name in dendrogram levels
	def _getDendrogramLevelByName(self, dendrogram, name):
		
		for level in range(0,len(dendrogram)):
			if dendrogram[level].SubName == name:
				return dendrogram[level]
		
		print("ERROR dendrogram level name >"+name+"< not found in _getDendrogramLevelByName")
		return None

	"""
	The edge distributions for each substructure do not contain information on edges that may have been compressed/deleted at
	a previous iteration. This restores the info by looking donwstream via @freqDist to determine the missing info.
	
	@dendrogram: The dendrogram, as a list of dendrogram objects
	@freqDist: The substructure frequency distribution; structurally this tells us how to traverse and recover the missing edge distribution information for each substructure

	NOTE: Requires that len(dendrogram) == number of tuples in freqDist, such that indices in @freqDist match indices in @dendrogram

	
	def _amendDendrogramEdgeDists(self, dendrogram, freqDist):
		print("Edge distributions before:")
		for level in range(len(dendrogram)):
			print(str(dendrogram[level].EdgeDist))
	
		#traverse graph of connected substructures from first substructure downstream, via freqDist structure
		for level in range(len(dendrogram) - 1):  #see _getDendrogramDistribution: subtract one, since the length of freqDist is len(dendrogram) -1; this does not result in loss of info, since we know the lowest leaf child will have its dist updated via its parents
			parent = dendrogram[level]
			if len(freqDist[level]) > 0:
				childDist = freqDist[level][0] #each member of freqDist is a tuple: ({'SUB0': 146, 'SUB1': 39, 'SUB2': 15}, 'SUB_init')
				parentEdgeDist = parent.EdgeDist #get all the edges that we deleted when this substructure was deleted
				parentVs = [edge[0] for edge in parent.SubGraphEdgeList]+[edge[1] for edge in parent.SubGraphEdgeList]
				parentVs = set(parentVs)
				
				#for this level, look at all of its children, and add any edges in its EdgeDist to its children, satisfying that these edges connect parent to the child
				for childName in childDist.keys():
					childLevel = self._getDendrogramLevelByName(dendrogram, childName)
					#get the set of all nodes in the child substructure
					childVs = [edge[0] for edge in childLevel.SubGraphEdgeList]+[edge[1] for edge in childLevel.SubGraphEdgeList]
					childVs = set(childVs)
					#print("CHILD VS: "+str(childVs))
					#look for nodes in edgeDist's dest/target nodes in @childVs; these will be added to the child per their frequency
					for edge in parentEdgeDist.keys():
						if edge[0] in parentVs and edge[1] in childVs:
							#print("APPENDING TO CHILD DIST: "+str(edge))
							if edge in childLevel.EdgeDist.keys():
								#note: this is permissible if/when a child has multiple parents
								childLevel.EdgeDist[edge] += parentEdgeDist[edge]
							else:
								childLevel.EdgeDist[edge] = parentEdgeDist[edge]
							#	print("ERROR: edge "+str(edge)+" already in child.EdgeDist in amendDendrogramEdgeDists(): "+str(childLevel.EdgeDist)) #A serious error; if reachble, then haven't understood the necessary parts of the structure ell enough
							#create a new member of the child's edge distribution
							#childLevel.EdgeDist[edge] = parentEdgeDist[edge]

		print("Edge distributions after:")
		for level in range(len(dendrogram)):
			print(dendrogram[level].SubName+"\t"+str(dendrogram[level].EdgeDist)+"  "+str(dendrogram[level].NumInstances)+" instances")
		"""
			
	"""
	For experimentation: search for metrics that distinguish outliers from anomalies, where loosely speaking, anomalies occur in the context of some
	sort of "normal" behavior. Think of having to identify anomalies using no threshold in terms of the size-reduction of compression levels.
	
	@dendrogram: Simply a list of CompressionLevels, with the last item representing the lowest trace/subs in the dendrogram
	"""
	def _analyzeDendrogram(self, dendrogram):
		threshold = 0.18
		numTraces = float(len(dendrogram[0].IdMap.keys()))
		#for now, just look at the least 10% or so of compressing traces, without parsing trace-graphs for graph comparison
		candidateIndex = -1 #the index in the compression level list (dendrogram) at which the number of ids drops below threshold in terms of frequency
		i = 0
		while i <  len(dendrogram):
			level = dendrogram[i]
			if (float(len(level.IdMap.keys())) / numTraces) <= threshold:
				candidateIndex = i
				break
			i += 1

		print("id map: "+str(dendrogram[0].IdMap))

		#Gets the distribution of a dendrogram, as a list of dictionaries
		freqDist = self._getDendrogramDistribution(dendrogram)
		print("FREQ DIST: "+str(freqDist))
		
		#CRITICAL: The timing of this is arbitrary and represents the bad coupling in this code:
		#At each compression iteration, edges are deleted; however edges incident to some substructure
		#could have been deleted on a previous iteration. This point in the code, freqDist in hand, 
		#just happens to be the point when we have the information to restore the upstream edge distribution information.
		#self._amendDendrogramEdgeDists(dendrogram, freqDist)
		
		
		
		#use the frequency distribution list to visualize the dendrogram as a graph (this embeds pageranks as well)
		dendrogramGraph = self._visualizeDendrogram(freqDist)
		#print the pagerank values per substructure
		print("Reverse PageRank Substructure Analysis:")
		for pair in sorted([(v["name"],v["reversePagerank"]) for v in dendrogramGraph.vs], key=lambda t: t[1], reverse=True):
			#get the traces from the substructure name
			traceIDs = self._getSubTraceIdsByName(dendrogram, pair[0])
			print(pair[0]+"  "+str(pair[1])[0:6]+"\t"+str(traceIDs))
		
		#maps substructure indices in the dendrogram (ints) to 
		entMap = self._getSubstructureEntropyMap(dendrogram,freqDist)
		[print(str(item)) for item in entMap.items()]
		cumEntMap = self._getCumulativeSubstructureEntropyMap(freqDist, entMap)
		
		#conditional probability based analysis
		childDists = self._analyzeChildSubDistributions(dendrogram)
		print("Child distributions: "+str(childDists))
		
		for i in range(0,len(dendrogram)):
			ids = self._getSubTraceIds(dendrogram, i)
			print(dendrogram[i].SubName+" ids:  "+str(ids))

		#analyze the connectivity of edges surrounding substructures vs. the overall graph distribution
		self._analyzeEdgeConnectivityDivergence(dendrogram)

		#now build the ancestry dict, mapping each id in the anomaly set to a tuple containing a list of compressing substructure ids higher in the hierarchy, and the cumulative compression value
		ancestryDict = {}
		candidateLevel = dendrogram[candidateIndex]
		candidateIds = candidateLevel.IdMap.keys()
		candidateIdSubMap = {} #the mapping from candidateIds to their respective elementary substructure at or below the candidate level; that is, binds the candidateIds to the most-compression substructure
		#build the candidate id-sub map, of ids to their most-compressing substructure (an index into the dendrogram levels)
		for id in candidateIds:
			level = int(candidateIndex)
			nextId = str(id)
			maxSubLevel = -1
			#print("id: "+nextId+" maxcomps: "+str(dendrogram[level].MaxCompressedIds))
			while level < len(dendrogram):
				if nextId in dendrogram[level].MaxCompressedIds:
					maxSubLevel = int(level)
					break
				else:
					nextId = dendrogram[level].IdMap[nextId]
				level += 1
			candidateIdSubMap[id] = maxSubLevel
		#the values of candidateIdSubMap, as a set, define the unique structures over which to search for anomalies and noise
		print("Candidate Id Base Substructure map: "+str(candidateIdSubMap))
		print("Candidate index: "+str(candidateIndex))
		
		#for each id among the candidates (outliers and anomalies), show their ancestry, rather their derivation in the dendrogram, if any
		print("candidate ids: "+str(sorted(candidateIds))+" for threshold "+str(threshold)+" from level "+str(candidateIndex))
		for id in candidateIds:
			#backtrack through the layers, showing the ancestry of this id, along with compression stats
			ancestry = [] #tuples of the form (SUB:numInstances:compFactor)
			cumulativeCompression = 0.0
			i = candidateIndex - 1
			curId = id #watch your py shallow copy...
			while i >= 0:
				curLevel = dendrogram[i]
				#print("level: "+curLevel.Line)
				curId = curLevel.ReverseIdMap[curId]
				#check if id was in the compressed set on this iteration/level; if so, append it to ancestry with other statistical measures
				if curId in curLevel.CompressedIds:
					#calculate simple KL divergence
					ancestry.append(i)
					cumulativeCompression += curLevel.CompressionFactor
				i -= 1
			#all (if any) ancestor level-indices appended to ancestry, so just add this list for this id
			ancestryDict[curId] = (ancestry,cumulativeCompression)

		#print, just to observe traits of anomalies
		print("Candidate-id Ancestry")
		print(str([(str(k),ancestryDict[str(k)]) for k in sorted([int(sk) for sk in ancestryDict.keys()])]))

		ancestorSubs = set()
		for pair in ancestryDict.items():
			for id in pair[1][0]:
				ancestorSubs.add(id)

		print("Ancestry set: "+str(ancestorSubs))
		
		
		#now, rather than searching over candidate ids, search over the space of anomalous substructures below candidate threshold
		j  = len(dendrogram) - 1
		ancestors = set()
		while j > i:
			#crawl up through dendrogram for all ancestors of this substructure
			ancestors |= self._getAncestorSet(j,dendrogram)
			j -= 1
		print("Ancestors: "+str(ancestors))
		
	
	"""
	Given a substructure, crawls up through the dendrogram and returns a list of ancestor structures.
	
	@baseIndex: The index from which to start the (upward) search through the dendrogram
	@dendrogram: a list of compressionLevels
	"""
	def _getAncestorSet(self,baseIndex,dendrogram):
		#crawl up through dendrogram for all ancestors of this substructure
		level = dendrogram[baseIndex]
		ancestors = set()

		for subId in level.CompressedIds:
			prev = int(baseIndex) - 1
			prevId = str(subId)
			while prev >= 0:
				ancestorLevel = dendrogram[prev]
				prevId = ancestorLevel.ReverseIdMap[prevId]
				if prevId in ancestorLevel.CompressedIds:
					ancestors.add(prev)
				prev -= 1

		return ancestors
		
	#Just a wrapper for building and then analyzing the dendrogram, for research
	def _dendrogramAnalysis(self, path):
		dendrogram = self._buildDendrogram(path)
		self._analyzeDendrogram(dendrogram)
	
	"""
	For now, this is without much nuance. Given a dendrogram, backtrack until the size of the trace subset is > threshold (eg 5%)
	of the overall size of the traces.
	@threshold: The dendrogram threshold; about 0.05 is about right
	"""
	def _compileDendrogramResult(self, threshold):
		anomalyIds = []
		compressionLevels = []
		f = open(self._dendrogramPath,"r")
		#parse the dendrogram file; the only important component is backtracking the trace-ids to their original ids
		for line in f.readlines():
			idMappings = line.split("{")[1].split("}")[0].split(",")
			newMap = {}
			for mapping in idMappings:
				prevId = mapping.split(":")[0]
				nextId = mapping.split(":")[1]
				newMap[prevId] = nextId
			compressionLevels.append(newMap)

		#print(str(compressionLevels))
		#get the total number of traces from the size of the first id-map
		numTraces = len(compressionLevels[0].keys())
		#march forward in compression levels until we reach the subset of traces whose size is less than some anomalousness threshold;
		#all these traces are anomalies. Once we have them, backtrack to their original id's.
		i = 0
		while i < len(compressionLevels) and float(len(compressionLevels[i])) / float(numTraces) > threshold:
			print("ratio: "+str(float(len(compressionLevels[i])) / float(numTraces)))
			i += 1
		print("i = "+str(i)+" numTraces="+str(numTraces))
		#check if anomalous group found; if so, backtrack to get their original ids
		if i > -1 and i < len(compressionLevels):
			#backtrack to the original ids; the keys in each level are the vals of the previous level
			prev = i - 1
			curKeys = compressionLevels[i].keys()
			print(str(curKeys))
			while prev >= 0:
				#print("curKeys: "+str(compressionLevels[i].keys()))
				#print("prev items: "+str(compressionLevels[prev].items()))
				#print("cur keys: "+str(compressionLevels[i].items()))

				prevKeys = []
				for k in curKeys:
					prevKeys += [pair[0] for pair in compressionLevels[prev].items() if pair[1] == k]
				#print("PKEYS: "+str(prevKeys))
				curKeys = [k for k in prevKeys]
				"""
				curKeys = []
				for pair in compressionLevels[prev].items():
					for k in compressionLevels[i].keys():
						if pair[1] == k:
							curKeys.append(pair[0])
				"""
				#curKeys = [pair[0] for pair in compressionLevels[prev].items() if pair[1] in compressionLevels[i].keys()]
				prev -= 1
				#i -= 1

			print("Dendrogram-based anomalies: ")
			curKeys = [int(k) for k in curKeys]
			curKeys = sorted(curKeys)
			print(str(curKeys))
			anomalyIds = curKeys
		else:
			print("Dendrogram-based anomalies:  >>no anomalies found<<")

		#report confusion matrix, other values
		self._outputResults(anomalyIds)


	"""
	Opens traces and gbad output, parses the anomalies and other data from them, necessary
	to compute false/true positives/negatives and then output them to file.
	"""
	def CompileResults(self):
		#compile and report the dendrogram results separately; this is sufficient for determining if the dendrogram-based methods even work
		if self._dendrogramPath != None:
			self._dendrogramAnalysis(self._dendrogramPath)
			self._compileDendrogramResult(self._dendrogramThreshold)

		#soon to be dead code: report recursive-gbad results
		self._reportRecursiveAnomalies()
		
		print("Result Reporter completed.")

	"""
	Feed this only a list of integer anomaly id's, and it automatically generates the confusion values,
	and displays the results

	@anomalies: a list of integer anomaly id's
	"""
	def _outputResults(self, anomalies):
		#MOVED TO CTOR
		#logFile = open(self._logPath, "r")
		#self._parseLogAnomalies(logFile)
		self._detectedAnomalyIds = anomalies
		
		#create the true anomaly and detected anomaly sets via the trace-id numbers
		truePositiveSet = set( [int(anomaly[0]) for anomaly in self._logAnomalies] )
		trueNegativeSet = set( [int(anomaly[0]) for anomaly in self._logNegatives] )
		detectedAnomalies = set(self._detectedAnomalyIds)

		#store overall stats and counts
		self._numDetectedAnomalies = detectedAnomalies
		self._numTrueAnomalies = len(self._logAnomalies)

		#get the false/true positives/negatives using set arithmetic
		self._truePositives = detectedAnomalies & truePositiveSet
		self._falsePositives = detectedAnomalies - truePositiveSet
		self._trueNegatives = trueNegativeSet - detectedAnomalies
		self._falseNegatives = truePositiveSet - detectedAnomalies

		#compile other accuracy stats
		self._errorRate = float(len(self._falseNegatives) + len(self._falsePositives)) / float(self._numTraces) #error rate = (FP + FN) / N = 1 - accuracy
		self._accuracy =  float(len(self._trueNegatives) + len(self._truePositives)) / float(self._numTraces) # accuracy = (TN + TP) / N = 1 - error rate

		#calculate precision: TP / (FP + TP)
		denom = float(len(self._falsePositives) + len(self._truePositives))
		if denom > 0.0:
			self._precision =  float(len(self._truePositives)) / denom
		else:
			self._precision = 0.0
		
		#calculate recall: TP / (TP + FN)
		denom = float(len(self._truePositives) + len(self._falseNegatives))
		if denom > 0.0:
			self._recall = float(len(self._truePositives)) / denom
		else:
			self._recall = 0.0
		
		#convert all sets to sorted lists
		self._truePositives = sorted(list(self._truePositives))
		self._falsePositives = sorted(list(self._falsePositives))
		self._trueNegatives = sorted(list(self._trueNegatives))
		self._falseNegatives = sorted(list(self._falseNegatives))

		self._displayResults()

	"""
	This may soon be dead code, based on better results with the delete-sub method:
	outputs anomalies found by recursive gbad, by which gbad is re-run on compressed
	subs.
	"""
	def _reportRecursiveAnomalies(self):
		gbadFile = open(self._gbadPath, "r")

		self._parseGbadAnomalies(gbadFile)
		#gbad doesn't always report all equivalent anomalies; this simply unifies all reported anomalies with traces that are the same
		self._detectedAnomalyIds = [int(trace[0]) for trace in self._unifyAnomalies()]
		self._outputResults(self._detectedAnomalyIds)
		
def usage():
	print("Usage: python ./AnomalyReporter.py -gbadResultFiles=[path to gbad output] -logFile=[path to log file containing anomaly labellings] -resultFile=[result output path] [optional: --dendrogram=dendrogramFilePath --dendrogramThreshold=[0.0-1.0] -markovPath=[path to markov file] -traceGraphs=[trace graphs path]")
	print("To get this class to evaluate multiple gbad result files at once, just cat the files into a single file and pass that file.")

"""

"""
def main():
	if len(sys.argv) < 5:
		print("ERROR incorrect num args")
		usage()
		exit()

	markovPath = ""
	traceGraphPath = ""
	gbadPath = sys.argv[1].split("=")[1]
	logPath = sys.argv[2].split("=")[1]
	resultPath = sys.argv[3].split("=")[1]
	dendrogramPath=None
	if len(sys.argv) >= 5 and "--dendrogram=" in sys.argv[4]:
		dendrogramPath = sys.argv[4].split("=")[1]

	dendrogramThreshold = 0.05
	if len(sys.argv) >= 6 and "--dendrogramThreshold=" in sys.argv[5]:
		dendrogramThreshold = float(sys.argv[5].split("=")[1])

	for arg in sys.argv:
		if "-markovPath=" in arg:
			markovPath = arg.split("=")[1]
		if "-traceGraphs=" in arg:
			traceGraphPath = arg.split("=")[1]
	if markovPath == "" or traceGraphPath == "":
		usage()
		exit()

	print("MARKOV: "+markovPath)
	reporter = AnomalyReporter(gbadPath, logPath, resultPath, markovPath, dendrogramPath, dendrogramThreshold, traceGraphPath)
	reporter.CompileResults()

if __name__ == "__main__":
	main()

