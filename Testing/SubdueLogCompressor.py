"""
Given a SUBDUE log and a file containing substructure prototypes, this compresses
the subdue log wrt the provided substructure.  It can also delete the substructure from 
all traces in which it occurs, deleting all vertices and in/out-edges to/from the substructure.

This script is to be used for a single compression, but as it does so, it will APPEND to dendrogram.txt
the compressed and non-compressed substructures in this format:
	([1,2,3]4,5,6:SUB_NAME)7,8,9
In reality, only two groups are important: those inside parans are all xp/trace ids that were compressed
by the compressing substructure; the brackets are just sugar to denote also those which reached max compression 
(they matched the substructure). The SUB_NAME is the ["name"] field given by the substructure. All ids outside the parens
are those traces that did not contain the subtructure and could not be compressed. Thus on each iteration a new line
is added to dendrogram.txt, giving a paraseable description of the graph's compression.

GBAD/SUBDUE output is all text-based, so this is annoying text-based for parsing the substructures
and subgraph log.
"""
from __future__ import print_function
import igraph
import sys
import re
import os

class LogCompressor(object):
	def __init__(self):
		self._compressedTraceIds = []
		#self._dendrogramFile = open("dendrogram.txt","a+")
		self._maxCompressedSubs = []
		self._compressedSubs = []
		self._nonCompressedSubs = []
		self._deletedSubs = []
		self._newXpIdCtr = 1
		
	"""
	Note this currently only takes the top substructure listed in the .g file.

	@logPath: The path to some .g log to be compressed
	@subsPath: The path to some gbad/subdue output text file containing best substructure prototypes (only the best substructure will be used)
	@outPath: The output path for the compressed log
	@compSubName: The name for the compressed substructure (eg, SUB1, SUB2... SUBi, where i may denote the number of recursive compressions so far)
	"""
	def Compress(self, logPath, subsPath, outPath, compSubName="SUBx", showSub=False, deleteSubs=False):
		print("Running SubdueLogCompressor on "+logPath+" using substructures from "+subsPath)
		print("Outputting compressed log to "+outPath+" with new compressed substructure named: "+compSubName)
		print("NOTE: once reduced to a single vertex (most compressed) substructure, the substructure will be looped to itself.")
		bestSub = self._parseBestSubstructure(subsPath)
		if bestSub != None:
			if showSub:
				layout = bestSub.layout("sugiyama")
				igraph.plot(bestSub, layout = layout, bbox = (1000,1000), vertex_size=35, vertex_label_size=15)
			
			bestSub["name"] = compSubName
			#save the substructure
			bestSub.write_graphml(bestSub["name"]+".graphml")
			#print(str(bestSub))
			subgraphs = self._buildAllTraces(logPath)
			#print("subgraphs:\n"+str(subgraphs)+"\nend subgraphs")
			compressedSubs, deletedSubs, edgeFreqs = self._compressAllTraces(subgraphs, bestSub, deleteSubs)
			#append to the dendrogram file
			self._appendToDendrogram(bestSub,compSubName, compressedSubs, deletedSubs, edgeFreqs)
			#print("compressed: "+str(compressedSubs)+"\nend compress subgraphs")
			self._writeSubs(compressedSubs, outPath)
		else:
			print("Compressor exiting with no compression")
			#output empty log to outPath
			ofile = open(outPath,"w+")
			ofile.close()

	"""
	Given a list of sub-graphs stored in igraph.Graph structures, write each one
	to a new output file, suitable as input to subdue/gbad. The graphs are newly labelled
	with incrementing id's, as required by gbad. Hence the id-mappings must preserved in other ways.

	@subs: A list of igraph structures representing .g traces
	@outPath: The path to which the new .g trace file will be written
	"""
	def _writeSubs(self,subs, outPath):
		ofile = open(outPath, "wb+") #the b and encode() notation below are just to force linux line endings

		for sub in subs:
			isValidSub = True #This check reflects a critical failure; if the messages below are detected, results are invalid, and fixes are needed upstream
			if len(sub.vs) == 0:
				print("ERROR empty sub detected  Edges: "+str(len(sub.es)))
				isValidSub = False
			if len(sub.vs) == 1:
				print("WARNING single-vertex sub detected.  Edges: "+str(len(sub.es)))
			if len(sub.es) == 0:
				print("ERROR zero edge substructure detected: "+sub["header"])
				isValidSub = False

			if isValidSub:
				xpNo = sub["header"][sub["header"].rfind(" ")+1:]
				#print("MAPPING "+xpNo+" -> "+str(i))
				#a hack required by gbad: "xp" declarations must be sequential
				sub["header"] = sub["header"][0:sub["header"].rfind(" ")]+" "+str(sub["newXpId"])
				ofile.write((self._sub2GFormatString(sub)+"\n").encode())

		ofile.close()

	"""
	Given a sub-graph .g trace in igraph form, converts the structure into a string formatted
	in .g format used by subdue/gbad.

	NOTE: This outputs using linux line endings

	returns: string representing this subgraph/trace in .g format
	"""
	def _sub2GFormatString(self,sub):
		vertexDict = {}
		s = sub["header"]+"\n"
		#build the vertex declarations
		i = 1
		for v in sub.vs:
			s += ("v "+str(i)+" \""+v["name"]+"\"\n")
			vertexDict[v["name"]] = i
			i += 1
			
		#build the edge declarations
		for e in sub.es:
			src = vertexDict[sub.vs[e.source]["name"]]
			dst = vertexDict[sub.vs[e.target]["name"]]
			s+= ("d "+str(src)+" "+str(dst)+" \"e\"\n")
			
		return s.rstrip()

	"""
	Checks if a sub-graph/trace is equal to some compressing substructure.
	This check is used to prevent compressing a graph with only one node--some
	compressing substructure--into nothing.
	"""
	def _traceEqualsSubgraph(self,subTrace, compSub):
		return (len(self._getNodeSet(subTrace)) > 0 and self._getNodeSet(subTrace) == self._getNodeSet(compSub) and len(self._getEdgeSet(subTrace)) > 0 and self._getEdgeSet(subTrace) ==  self._getEdgeSet(compSub))

		#note < and > check for proper subsets
		#return len(compNodeSet.difference(subNodeSet)) == 0 and len(compEdgeSet.difference(subEdgeSet)) == 0
		

	"""
	Deletes a substructure from a trace. This is nuanced, since clients (eg gbad) may handle
	the results (potentially disconnected graphs) poorly, since potentially-disconnected graphs
	are a likely edge-case not covered by graph algorithm implementation testing.

	@traceSub: a trace/subgraph
	@compSub: a prototype substructure by which to attempt to compress traceSub

	Return Cases:
	
		Returns: delSub (deleted substructure) and delEdges (incident and out-edges of a deleted substructure wrt compressing sub)
		@delEdges can be empty when a substructure reaches maximum compression: the only remaining components are deleted, and therefore not connected to anything.
	
		1) trace does not contain sub: just return the trace unmodified, empty edge list
		2) trace PROPERLY contains substructure: The substructure is deleted from the trace.
		This may result in single vertices with no edges, which will be returned with a single reflexive loop.
		This is just so clients can handle disconnected vertices, since its foreseeable their code was not written to handle edgeless nodes.
		3) trace EQUALS substructure: the trace is discarded and None is returned
	"""
	def _deleteTraceSub(self, traceSub, compSub):
		#delEdges is a list of named tuples reflecting directed edges: [('a','b'), ('c','b') ... ]
		delEdges = [] #delEdges only takes a non-empty value if the trace is compressed wrt compSub, but not maximally compressed (one or more edges connect them)
		delSub = traceSub

		#trace contains subgraph, so delete it as described above
		if self._traceContainsSubgraph(traceSub, compSub):
			self._compressedSubs.append(traceSub["oldXpId"])
			#trace equals subgraph, so entire trace should be deleted: set result to None and return
			if self._traceEqualsSubgraph(traceSub,compSub):
				self._maxCompressedSubs.append(traceSub["oldXpId"])
				#print("EQUALITY")
				delSub = None
			else:
				#print("CONTAINMENT: g1"+str([v["name"] for v in traceSub.vs]))
				#print("g2: "+str([v["name"] for v in compSub.vs]))
				#get the vertex and edge sets for each subgraph
				vsTrace = set([v["name"] for v in traceSub.vs])
				vsComp = set([v["name"] for v in compSub.vs])
				esTrace = set([(traceSub.vs[e.source]["name"], traceSub.vs[e.target]["name"]) for e in traceSub.es])
				esComp = set([(compSub.vs[e.source]["name"], compSub.vs[e.target]["name"]) for e in compSub.es])
				#subtract the compressing substructure vertices, edges, from the trace
				vsDel = vsTrace - vsComp
				#delete the edges within or incident to/from the compressing substructure
				esDel = set([e for e in esTrace if e[0] not in vsComp and e[1] not in vsComp])
				#build delEdges from the set of edges connecting traceSub and compSub
				delEdges = [e for e in esTrace if (e[0] not in vsComp and e[1] in vsComp) or (e[1] not in vsComp and e[0] in vsComp)]
				#print("\n\nDEL EDGES: "+str(delEdges))
				#print("vsDel: "+str(vsDel))
				#print("esDel: "+str(esDel))
				#print("trace vs: "+str(vsTrace))
				#print("comp vs: "+str(vsComp))
				#print("trace es: "+str(esTrace))
				#print("comp es: "+str(esComp))
				#check for vertices associated with no edges, and add reflexive edges to them
				for v in vsDel:
					hasEdge = False
					for e in esDel:
						hasEdge |= (e[0] == v or e[1] == v)
					#vertex has no associated edge so add a reflexive edge to it
					if not hasEdge:
						esDel.add((v,v))

				#print("vsDel: "+str(vsDel))
				#print("esDel: "+str(esDel))

				#create the new sub
				delSub = igraph.Graph(directed=True)
				#preserve the trace header
				delSub["header"] = traceSub["header"]
				delSub["name"] = compSub["name"]
				#add the vertices and edges as created above
				delSub.add_vertices(list(vsDel))
				delSub.add_edges(list(esDel))
		else:
			#append to non-compressed traces
			self._nonCompressedSubs.append(traceSub["oldXpId"])

		return delSub, delEdges

	"""
	Given a trace subgraph from the log and a compressing substructure, 
	this compresses the subgraph wrt to the compressing substructure. If
	the compressing substructure is not contained within the traceSub,
	traceSub is returned unchanged. Else, the compressing substructure is replaced
	by a single node "SUB1" with all in/out edges to the substructure sutured
	accordingly to SUB1.

	There are actually three cases:
		1) Trace doesn't contain substructure: so just return trace
		2) Trace properly contains substructure: compress the trace wrt the substructure
		3) Trace equals the substructure: This is an exception/edge case, for which the
		compressing substructure must be returned, with a single loop to itself (since subdue/gbad
		probly requires at least one edge)

	@traceSub: a trace/subgraph
	@compSub: a prototype substructure by which to attempt to compress traceSub
	"""
	def _compressTraceSub(self,traceSub, compSub):
		compressed = traceSub
		if self._traceContainsSubgraph(traceSub, compSub):
			self._compressedSubs.append(traceSub["oldXpId"])
			#see header: return the compressing substructure with one reflexive loop
			if self._traceEqualsSubgraph(traceSub, compSub) and len(compSub.vs) == 1:
				self._maxCompressedSubs.append(traceSub["oldXpId"])
				print("MAX COMPRESSION")
				#just copy the sub and add a reflexive loop
				compressed = igraph.Graph(directed=True)
				#preserve the trace header
				compressed["header"] = traceSub["header"]
				compressed["name"] = compSub["name"]
				
				#prepare the compressed sub with a single node and single reflexive edge
				compNodeSet = self._getNodeSet(compSub)
				if len(compNodeSet) == 0:
					compressed.add_vertices([compSub["name"]])
				else: #else add whatever vertices the compressed structure already had
					vertices = [v["name"] for v in compSub.vs]
					compressed.add_vertices(vertices)
				
				compEdgeSet = self._getEdgeSet(compSub)
				if len(compEdgeSet) == 0:
					#add a single reflexive loop
					compressed.add_edges([(compSub.vs[0]["name"], compSub.vs[0]["name"])])
				else:
					compressed.add_edges(list(compEdgeSet))	
			#trace properly contains the substructure, so compress wrt it
			else:
				#print("CONTAINMENT")
				#build a new, compressed subgraph from scratch, but keeping the old one's indentifying header
				compressed = igraph.Graph(directed=True)
				#preserve the header
				compressed["header"] = traceSub["header"]
				#use set arithmetic to compress the trace wrt the compressing substructure
				compEdgeSet = self._getEdgeSet(compSub)
				traceEdgeSet = self._getEdgeSet(traceSub)
				compNodeSet = self._getNodeSet(compSub)
				traceNodeSet = self._getNodeSet(traceSub)
				
				#get new vertices (all vertices minus the compressing ones) by name
				newVertices = [v for v in traceNodeSet.difference(compNodeSet)]
				#print("old vertices: "+str(traceNodeSet))
				#print("new vertices: "+str(newVertices))
				newVertices += [compSub["name"]] #add the new metanode
				newEdges = []
				#build the edge set, redirecting all in-edges to the substructure to point at SUB1, all out-edges from the substructure to point from SUB1
				for e in traceEdgeSet:
					#detect edges incident to substructure
					if e[0] not in compNodeSet and e[1] in compNodeSet:
						newEdges.append((e[0],compSub["name"]))
					#detect out-edges from substructure
					elif e[0] in compNodeSet and e[1] not in compNodeSet:
						newEdges.append((compSub["name"],e[1]))
					#detect edges unconnected to substructure
					elif e[0] not in compNodeSet and e[1] not in compNodeSet:
						newEdges.append(e)
					#lastly, no else: ignore edges internal to the substructure
				
				if len(newVertices) == 0: #tracks a specific defect I had
					print("ERROR newVertices empty in SubdueLogCompressor._compressTraceSub()")
				
				if len(newEdges) < len(newVertices) - 1: #just a potential error, for disconnected graphs
					print("ERROR numEdges < numVertices in SubdueLogCompressor")
					
				#loop the single vertex back to itself when it has reached max compression
				if len(newEdges) == 0 and len(newVertices) == 1:
					#print("reflecting max compressed graph")
					newEdges.append((newVertices[0],newVertices[0]))

				#print(str(newVertices))
				compressed.add_vertices(newVertices)
				#print(str(newEdges))
				compressed.add_edges(newEdges)
		else:
			#else do nothing, just add trace to uncompressed list
			self._nonCompressedSubs.append(traceSub["oldXpId"])
				
		return compressed
		
	"""
	Given the list of compressed and uncompressed traces, appends a string to the dendrogram.txt
	file as described in the header: ([1,2,3]4,5,6:SUB_NAME)7,8,9
	Additionally, the id mapping is appended, indicating the mapping of old xp-ids to new one's. This is a defect of
	SUBDUE/gbad, which requires sequentially incrementing id's, starting at 1. Hence removing any traces breaks
	the sequence, and gbad crashes. A new sequence is generated, so the map string just preserves the id mappings as:
		{1:2,4:4,3:-1} 
	Here, the old xp-id '1' maps to '2' in the new compressed log, 4 to 4, and 3 is set to -1 to indicate it was removed
	and is not in the new log.
	
	THIS IS SERIALIZATION: CHANGE THIS CODE AND THE DESERIALIZATION IN ANOMALYREPORTER/DENDROGRAM.PY ARE BROKEN
	
	@edgeFreqs: A frequency table of ('a','b') -> freq  key/value pairs giving the distribution of edges for this substructure. Often this will be empty. It
	is passed along as information stuffed into the dendrogram.txt file
	"""
	def _appendToDendrogram(self, compSub, compSubName, compressedSubs, deletedSubs, edgeFreqs):
		s = "("
		#add the max compressed ids
		if len(self._maxCompressedSubs) > 0:
			s += "["
			for name in self._maxCompressedSubs:
				s += str(name+",")
			s = s[:-1] #snip the last comma
			s += "]"
		else:
			s += "[]"
		#add the rest of the compressed ids
		for name in self._compressedSubs:
			s += str(name+",")
		s = s[:-1]    #snip the last comma
		#s += (":" + compSubName + ")") #add sub info
		s += (":" + compSubName + ":"+str(compSub["instances"])+":"+str(compSub["compValue"])+")") #add sub info
		#add the noncompressed trace ids
		if len(self._nonCompressedSubs) > 0:
			for name in self._nonCompressedSubs:
				s += (name+",")
			#snip the last comma
			s = s[:-1]

		#build the mapping string; this preserves the trace-id mapping info across iterations, since they change
		mstr = "{"
		for sub in compressedSubs:   #the traces that will be preserved in the next iteration
			#FAILING HERE??? Don't forget to pass --deleteSubs
			mstr += (str(sub["oldXpId"]) + ":" + str(sub["newXpId"]) + ",")
		if len(deletedSubs) > 0:	
			for sub in deletedSubs: #the traces that were removed on this iteration; these will point to -1 to indicate their removal
				mstr += (str(sub["oldXpId"]) + ":-1,")
		mstr = mstr[:-1] #snip the last comma
		mstr += "}"
		
        #add the complete graph description of the compressing substructure as a csv list of edges as v1->v2 directed pairs
		mstr += "#"
		mstr += str(list(self._getEdgeSet(compSub)))

		#add the distribution of edges that connected to the compressing substructure; this will often be empty, such as when no edges remain
		mstr += "#"
		mstr += str(edgeFreqs)
		
		"""
		for edge in compSub.es:
		mstr += (compSub.vs[edge[0]]["name"]+"->"compSub.vs[edge[0]]["name"]+",")
		#delete the lastly appended comma
		mstr = mstr[0:len(mstr)-1]
		"""

		f = open("dendrogram.txt","a+")
		f.write(s+mstr+"\n")
		f.close()

	"""
	Given a igraph Graph g representing a subgraph/trace from the gbad input,
	returns all edges as a set of named pairs (source, dest).
	"""
	def _getEdgeSet(self,g):
		return set([(g.vs[e.source]["name"], g.vs[e.target ]["name"]) for e in g.es])
		
	"""
	Returns the list of node names in some graph g.
	"""
	def _getNodeSet(self,g):
		return set([v["name"] for v in g.vs])

	"""
	Detects whether or not a particular trace subgraph contains some compressing substructure.

	@subTrace: An igraph representation of a trace in the .g log
	@compSub: A compressing substructure also represented as an igraph

	Returns: True if the subtrace contains (and may be equal to) the compSub
	"""
	def _traceContainsSubgraph(self,subTrace, compSub):
		subNodeSet = self._getNodeSet(subTrace)
		compNodeSet = self._getNodeSet(compSub)
		subEdgeSet =  self._getEdgeSet(subTrace)
		compEdgeSet = self._getEdgeSet(compSub)

		#print("sub ["+subTrace["header"]+": "+str(subNodeSet)+"\ncomp: "+str(compNodeSet))
		#print("subed: "+str(subEdgeSet)+"\ncomped: "+str(compEdgeSet))
		
		#note < and > check for proper subsets
		return compNodeSet.issubset(subNodeSet) and compEdgeSet.issubset(subEdgeSet)


	"""
	Given a list of traces subgraphs, and an instance of the best substructure found by subdue/gbad,
	this compresses all subgraphs wrt the best substructure. If the trace does not contain the substructure,
	the trace is preserved in its current form. If the trace does contain the substructure, then the entire
	substructure is replaced with a single node "SUB1", and all in/out edges to/from the structure are woven
	into this metanode.

	@traceSubs: All traces (subgraphs) in the original log
	@bestSub: Best-compressing substructure wrt which this log will be compressed
	@deleteSub: Flag, if true, delete all substructure instances instead of compressing them
	
	Returns: List of compressed subs, the deleted subs (only meaningful/non-empty if deleteSub=True), and edge frequencies for each
	"""
	def _compressAllTraces(self, traceSubs, bestSub, deleteSub=False):
		compressedSubs = []
		deletedSubs = []
		connectingEdgeFreqs = dict() #the edge collection; this is constructed as a frequency table since in/out edges may not occur the same in every compressable trace (although this will normally be true)
		
		for trace in traceSubs:
			#if deleteSub, delete the substructure; if no vertices remain, the subgraph is no longer in the trace
			if deleteSub:
				#print("DELETING SUB: "+bestSub["name"])
				sub, connectingEdges = self._deleteTraceSub(trace, bestSub)
				#record connecting edges for this trace and bestSub
				for edge in connectingEdges:
					if edge in connectingEdgeFreqs.keys():
						connectingEdgeFreqs[edge] += 1
					else:
						connectingEdgeFreqs[edge] = 1

				#if sub is None (entire subgraph was deleted), just ignore it
				if sub is not None:
				
					#bug check
					if len(sub.vs) == 0:
						print("ERROR empty sub detected  Edges: "+str(len(sub.es)))
					if len(sub.vs) == 1:
						print("WARNING single-vertex sub detected.  Edges: "+str(len(sub.es)))
				
				
				
					sub["oldXpId"]  = trace["oldXpId"]
					sub["newXpId"] = self._newXpIdCtr
					self._newXpIdCtr += 1
					compressedSubs.append(sub)
					#print("appended: "+str(sub))
				else:
					deletedSubs.append(trace)
			else:
				sub = self._compressTraceSub(trace, bestSub)
				compressedSubs.append(sub)

		return compressedSubs, deletedSubs, connectingEdgeFreqs
		

	"""
	Given a .g log formatted as input to gbad/subdue, builds a 
	Note that this will disregard comments in the log.

	@logPath: Path to compressed.g log
	
	Returns: A list of subgraphs representing all traces in the log, as igraph.Graphs. The vertices of the
	subgraphs preserve the gbad input vertex ids in the vertex "subdueId" attribute (eg, g.vs[1]["subdueId"])
	"""
	def _buildAllTraces(self, logPath):
			logFile = open(logPath,"r")
			subgList = []
			
			i = 0
			lines = [line.strip() for line in logFile.readlines()]
			logFile.close()
			
			#chop header string, if there is one
			if lines[0][0:2] != "XP":
				lines = lines[1:]
			fileStr = "\n".join(lines)
			#print("FILESTR: "+fileStr)
			
			if "~" in fileStr:
				print("ERROR tilde used as special anchor in _buildAllTrace. File may not contain tildes.")

			xpTokens = ["XP "+token.strip() for token in fileStr.split("XP") if len(token.strip()) > 0]
			xpTokens = [token.replace("\n","~") for token in xpTokens]
			
			#xpTokens = [token.replace("\n","~").replace("~~","~") for token in fileStr.replace("XP","~XP").split("~") if len(token.strip()) > 0]
			#for token in xpTokens:
			#	print(token)
			#exit()
			#convert all 'XP' strings to subgraphs
			#print("BuildAll ("+logPath+"): "+xpTokens[0])
			subgList = [self._subDeclarationToGraph(xpToken) for xpToken in xpTokens]

			return subgList

	"""
	Assumptions: the .g substructures are all "d" edges.

	Returns: The best substructure, as an igraph.Graph structure.
	"""
	def _parseBestSubstructure(self,subsPath):
		vertexDict = {}
		edges = []

		#get the raw subs file string (gbad/subdue output) (replacing linefeeds with some temp pattern makes things easier for re's)
		subsRaw = open(subsPath,"r").read().replace("\r\n","\n").replace("\n","~")
		#print("raw subs:\n"+subsRaw)
		if len(subsRaw) < 50:
			print("WARNING Possibly empty substructure file detected. Contents:\n"+subsRaw)
			return None

		#find the substructures just given a textual anchor pattern: "Normative Pattern (" followed by stuff, followed by double line-feeds
		start = subsRaw.find("Normative Pattern (")
		#write out the number of instances to file; this is just hacky comms with external processes that use the LogCompressor
		subCt = subsRaw.split(", instances = ")[1].split("~")[0]
		compValue = float(subsRaw.split("Substructure: value = ")[1].split(",")[0])
		#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		#Here I'm directly calculating the target gbad-threshold, which really has no business in the Log Compressor
		gbadThreshold = float(subCt) / 200.0 - 0.2
		gbadThreshold = min(0.4, max(gbadThreshold,0.05))
		print("Writing subs-count to ./subsCount.txt with COMPRESSOR SUB_CT="+subCt+" threshold "+str(gbadThreshold))
		open("gbadThresh.txt","w+").write(str(gbadThreshold))
		#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		#print("start: "+str(start))
		subsRaw = subsRaw[start : subsRaw.find("~~",start)] #gets the "Normative Pattern.*\n\n" string
		#find the precise start of the vertex declarations
		subsRaw = subsRaw[ subsRaw.find("    v ") : ]
		#print("subs raw: "+subsRaw)
		sub = self._subDeclarationToGraph(subsRaw,hasXpHeader=False)
		#store additional data in the graph
		sub["instances"] = int(subCt)
		sub["compValue"] = compValue
		
		return sub
		
	"""
	Converts a substructure (subgraph) declaration string in .g format to an igraph.Graph structure.

	@subStr: The substructure string starting with 'XP' and newlines replaced with tilde
	but with all newlines replaced by tilde (just a parsing trick).
	@hasXpHeader: Whether or not @subStr begins with 'XP # 123'. The gbad output of the best substructure doesn't have this.
	
	Returns: The igraph.Graph structure representing this substructure, having node "name"/"label" attributes
	that coincide with the declared vertex names.
	"""
	def _subDeclarationToGraph(self, subStr, hasXpHeader=True):
		substructure = igraph.Graph(directed=True)
		vertexDict = {}
		edges = []
		
		#print("HasXpHeader: "+str(hasXpHeader))
		#print("SUBSTR: "+subStr)
		
		lineTokens = subStr.split("~")

		#utilitarian logic for this function, just facilitates parsing logic via @tokenBegin
		if hasXpHeader:
			#print("HERE: "+str(lineTokens[0]))
			substructure["header"] = lineTokens[0]
			
			if "#" not in lineTokens[0]:
				print("DEAD: ")
				for token in lineTokens:
					print("tok: "+token)
			
			substructure["oldXpId"] = lineTokens[0].split("#")[1].strip()
			tokenBegin = 1
		else:
			tokenBegin = 0
			
		#within the string, find all the "v" and "d" (edge) declarations
		for line in lineTokens[tokenBegin:]:
			ln = line.strip()
			if len(ln) > 2:
				#parse a vertex declaration
				if "v " == ln[0:2]:
					vName = ln.split("\"")[1]
					vId = int(ln.split(" ")[1])
					vertexDict[vId] = vName
				#parse an edge declaration (the labels are meaningless; and all are assumed DIRECTED)
				elif "d "== ln[0:2]:
					e = (int(ln.split(" ")[1]), int(ln.split(" ")[2]))
					edges.append(e)

		#print(str(edges))
		#print(str(vertexDict))
		
		#add all of the vertices
		#substructure.add_vertices(vertexDict.values())
		#add all of the edges (by name)
		edges = [(vertexDict[e[0]], vertexDict[e[1]]) for e in edges]
		vertices = []
		for e in edges:
			vertices.append(e[0])
			vertices.append(e[1])
		vertices = list(set(vertices))
		#print("adding vertices: "+str(vertices))
		substructure.add_vertices(vertices)
		#preserve the subdue vertex id's as strings (it may be useful to preserve these)
		for v in substructure.vs:
			for k in vertexDict.keys():
				if vertexDict[k] == v["name"]:
					v["subdueId"] = str(k)
		
		#copy name as label attributes of vertices for display
		for v in substructure.vs:
			v["label"] = v["name"]
		
		#print("adding edges: "+str(edges))
		substructure.add_edges(edges)
				
		return substructure

				
def usage():
	print("usage: python SubdueLogCompressor.py [subgraph .g file] [substructure prototype file (subdue/gbad text output)] [output path for new compressed .g log] [optional: name=name of compressed structure]")
	print("--showSub: pass to display the parsed substructure")
	print("--deleteSub: pass to delete the substructure from the log. Single node w/out edges will be converted to reflexive nodes.")
	print("WARNING make sure input has only single line-feed line terminals (linux style), not windows style!!")

if __name__ == "__main__":	
	if len(sys.argv) < 4:
		for arg in sys.argv:
			print(arg)
		print("Incorrect num parameters ("+str(len(sys.argv))+") passed to SubdueLogCompressor.py.")
		usage()
		exit()

	if "linux" not in os.name.lower():
		print("WARNING non-Linux OS detected. Make sure all input to SubdueLogCompressor.py has linux style line endings (single line-feeds),")
		print("not windows style CR+LF. All output will preserve linux-format.")

	inputLog = sys.argv[1]
	subsFile = sys.argv[2]
	outputLog = sys.argv[3]
	if len(sys.argv) > 4 and "name=" in sys.argv[4]:
		compSubName = sys.argv[4].split("=")[1]
	else:
		compSubName = "SUBx"

	deleteSub = "--deleteSubs" in sys.argv or "--deleteSubs=true" in sys.argv
	showSub = "--showSub" in sys.argv
	
	compressor = LogCompressor()
	compressor.Compress(inputLog, subsFile, outputLog, compSubName, showSub, deleteSub)
