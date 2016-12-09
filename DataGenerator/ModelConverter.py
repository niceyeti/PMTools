import igraph
import copy
import sys
import os

"""
TODO: If this is ever used again, factor out the ModelGenerator and ModelConverter into separate objects, and
embed them in some other object, eg "SyntheticModelFactory".
"""

"""
Given a process-model string as output by ModelGenerator.py, this builds a graph structure based on 
the process-model using the igraph api. igraph is a powerful api for building, maintaining, traversing,
and serializing graphs.

Input: a process-model string as described by ModelGenerator.py
Ouput: a directed, edge-weighted graph in graphML. Such a graph can then be transferred to any
other object for generating data.
"""
class ModelConverter(object):
	def __init__(self):
		self._graph = None
		self._operators = "()&|[]"
		self._validActivityChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0987654321_^$!"
		#Unique characters for tracking the start and end node. These must not exist in the symbols of the input model string.
		self._startNodeName = "$"
		self._endNodeName = "!"
		#The number of empty branches encountered, allowing them to be labelled uniquely. This is so different '^' branches don't resolve to the same node.
		self._emptyBranchCtr = 0
		#plotting colors for anomalous/normal edges
		self._anomalyColor = "orange"
		self._normalColor = "black"

	"""
	Looks up the nodeId (usually just its numeric index) in the igraph vs container.
	Returns -1 if node not found, which will occur often as new empty branches are created.
	"""
	def _getNodeId(self,nodeName):
		for v in self._graph.vs:
			if v["name"] == nodeName:
				return v.index
		return -1

	def _generateUniqueEmptyNodeLabel(self):
		self._emptyBranchCtr += 1
		vLabel = "^_"+str(self._emptyBranchCtr)				
		return vLabel

	"""
	Adds a layer of indirection between model-string characters (A,B,C, etc) so that we can catch '^' empty branches
	as they arrive and assign unique labels to them.
	
	@alpha: Some model-string character/non-operator, such as "ABC..." and also including "^".
	"""
	def _getActivityLabel(self,alpha):
		if alpha == "^":
			activity = self._generateUniqueEmptyNodeLabel()
		else:
			activity = alpha

		return activity
		
	"""
	Utility for creating nodes. Ideally, this function should not be called, and all activities/nodes should be constructed ahead of time.
	In fact, adding vertices one at a time in igraph is very inefficient. However, this method is to create nodes on the fly, whose existence
	we can't know at preprocessing time, such as empty branches to which unique labels must be assigned to disambiguate em.
	"""
	def _createNode(self,vName):
		self._graph.add_vertex(vName)
		#vertex added, now go look it up so we can decorate some more. This inefficiency is just part of the igraph api.
		vId = self._getNodeId(vName)
		self._graph.vs[vId]["label"] = vName
		return vId

	"""
	Utility for adding edges etween activities. This also handles the corner case of empty branches '^', vertices which are labelled uniquely
	as they are encountered. This preserves the uniqueness of each empty branch, so they don't all collapse to the same ambiguous '^' node.
	
	@activity1: The single char activity id
	@activity2: The dest, single-char activity id
	@pEdge: This edge's probability
	@isAnomalous: Whether or not this should be labelled an anomalous edge. This is used/detect later when traversing the graph stochastically.
	@edgeType: The structure type to which the edge belongs, one of SEQ (simple sequential), OR, LOOP, or AND.
	"""
	def _addEdge(self,activity1,activity2,pEdge=1.0,isAnomalousEdge=False,edgeType="SEQ"):
		v1 = self._getActivityLabel(activity1)
		v2 = self._getActivityLabel(activity2)
		v1Id = self._getNodeId(v1)
		#if node is not found, create it. The only path here is when unique empty branches are created as they stream in, hence these vertices weren't made beforehand.
		if v1Id < 0:
			v1Id = self._createNode(v1)
		#same as above
		v2Id = self._getNodeId(v2)
		if v2Id < 0:
			v2Id = self._createNode(v2)

		if v1Id < 0:
			print("ERROR v1Id < 0 in _addEdge()")
		if v2Id < 0:
			print("ERROR v2Id < 0 in _addEdge()")
			
		#only add a directed edge if it doesn't already exist. Note this prevents multigraphs.
		if not self._edgeExists(v1Id,v2Id):
			if isAnomalousEdge:
				color = self._anomalyColor
			else:
				color = self._normalColor

			self._graph.add_edge(v1Id, v2Id,probability=pEdge,isAnomalous=isAnomalousEdge,color=color,type=edgeType)
			#set the anomalous flag
			#eid = self._graph.get_eid(v1Id,v2Id)
			#self._graph.es[eid]["isAnomalous"] = bool(isAnomalous)
			#if isAnomalous:
			#	self._graph.es[eid]["color"] = "yellow"
			#else:
			#	self._graph.es[eid]["color"] = "black"
		else:
			#this should be unreachable; notify if not
			print("WARNING edge already exists: "+activity1+" -> "+activity2)
			
	"""
	Check if an edge exists, based on their integer id's.
	"""
	def _edgeExists(self,v1Id,v2Id):
		try:
			hasEdge = self._graph.get_eid(v1Id,v2Id) >= 0
		except igraph._igraph.InternalError:
			hasEdge = False
		
		return hasEdge
	"""
	Given a string beginning with an AND/OR expression "(", this parses the expr arguments and operator,
	returning a tuple of (leftArg,rightArg,operator,remainder).
	
	Given: "(A | (B | C))ABC..." this function returns a tuple (A,(B|C),"|","ABC...")
	Returns: leftExpr, pLeft, rightExpr, pRigh, opString, remainderString
	
	"""
	def _parseAndOrExpr(self,modelString):
		if modelString[0] != "(":
			print("PARSE ERROR non-AND/OR substring passed to be parsed by _parseAndOrExpr(): "+modelString)
			print("Exiting disgracefully")
			exit()
	
		#find open/close parens of expr, and the position of the operator (& or |)
		i = 1
		operatorIndex = -1
		unmatchedParens = 1
		while unmatchedParens > 0: #find span of left and right parens
			if modelString[i] == "(":
				unmatchedParens += 1
			if modelString[i] == ")":
				unmatchedParens -= 1

			#when unmatchedParens==1, an operator is in scope of this expression
			if unmatchedParens == 1 and modelString[i] in "|&":
				operatorIndex = i

			if unmatchedParens > 0:
				i += 1
		#post loop: i points to index of closing paren for this expression, operatorIndex points to index of operator (| or &)
		#print("MODEL STRING: "+modelString)
		#print("REMAINDER: "+modelString[i:])
		
		operator = modelString[operatorIndex]
		j = i
		if operator == "|":
			#next, for OR exprs only, grab the probability tuple "(...):<0.2,0.8>"
			while modelString[j] != ">":
				j+=1
			#post-loop: j points to index of ">"
			
			#get the probability expressions: "<0.2/True,0.8/False>"  -->  ["0.2/True","0.8/False"]
			probExprs = modelString[i+1:j].replace(">","").replace(":","").replace("<","").split(",")
			pLeft,isLeftAnomaly = self._parseBranchAttributes(probExprs[0])
			pRight,isRightAnomaly = self._parseBranchAttributes(probExprs[1])
		else: #else this is an AND expression, which have no probabilities or anomalous characteristics
			pLeft = 1.0
			pRight = 1.0
			isLeftAnomaly = False
			isRightAnomaly = False
			
		leftArg = modelString[1:operatorIndex]
		rightArg = modelString[operatorIndex+1:i]
		operator = modelString[operatorIndex]
		remainder = modelString[j+1:]
		#print("pleft,pright: "+str(pLeft)+"  "+str(pRight))
		#print("leftArg: "+leftArg)
		#print("rightArg: "+rightArg)
		#print("operator: "+operator)
		#print("remainder: "+remainder)
		
		return (leftArg,pLeft,isLeftAnomaly,rightArg,pRight,isRightAnomaly,operator,remainder)

	"""
	Given branch attributes, returns probability and isAnomaly as a tuple.
	Example: "0.2/False" returns a tuple (0.2,False)
	"""
	def _parseBranchAttributes(self,expr):
		pBranch = float(expr.split("/")[0])
		isAnomaly = expr.split("/")[1].lower() == "true"
		return pBranch,isAnomaly
	
	"""
	Detects whether or not this alpha is an activity: either a base activity or "^".
	"""
	def _isActivity(self,alpha):
		return alpha in self._activities or alpha == "^"
	
	"""
	The recursive model string parser.
	"""
	def _convert(self,rModelString, rLastActivities):
		#base case
		if len(rModelString) == 0:
			return ([],[])
	
		firstActivities = []
		#foolish pythonic method to deep copy the recursive args
		modelString = rModelString + ""
		lastActivities = rLastActivities + []
		#print("CONVERT modelstr: "+modelString)
		
		#if self._isActivity(modelString[0]):
		#	#save the first activity, to be returned as this subprocess' input
		#	activity = self._getActivityLabel(modelString[0])
		#	firstActivities = [activity]

		i = 0
		while i < len(modelString):
			if self._isActivity(modelString[i]):
				activity = self._getActivityLabel(modelString[i])
				#connect simple, linear activities: A->B
				for lastActivity in lastActivities:
					self._addEdge(lastActivity, activity, 1.0, False, "SEQ")
				lastActivities = [activity]
				#initialize the input activities, if not yet inited
				if len(firstActivities) == 0:
					firstActivities = [activity]
				i += 1
				
			elif modelString[i] == "(":
				leftExpr, pLeft, isLeftAnomaly, rightExpr, pRight, isRightAnomaly, opString, modelString = self._parseAndOrExpr(modelString[i:])
				leftInputs, leftOutputs = self._convert(leftExpr,[])
				rightInputs, rightOutputs = self._convert(rightExpr,[])
				if opString == "|":
					opLabel = "OR"
				else:
					opLabel = "AND"
				#configure the inputs for the left branch
				for activity in leftInputs:
					for lastActivity in lastActivities:
						self._addEdge(lastActivity, activity, pLeft, isLeftAnomaly, opLabel) #only the input edges are marked as OR-type
				#configure the inputs to the right branch
				for activity in rightInputs:
					for lastActivity in lastActivities:
						self._addEdge(lastActivity, activity, pRight, isRightAnomaly, opLabel)
				#update last activities
				lastActivities = [self._getActivityLabel(activity) for activity in leftOutputs + rightOutputs]
				#set firstActivities, if empty. This is a small exception, is this function was called on a subexpr, eg "((AB...". The same exception does not apply to loops ("["), since they are constained to start with some activity
				if len(firstActivities) == 0:
					firstActivities = [self._getActivityLabel(activity) for activity in leftInputs + rightInputs]
				#print("LAST: "+str(lastActivities))
				i = 0 #reset to zero, since modelString is reset to remainder of string after sub-expr
				
			elif modelString[i] == "[":
				loopExpr, pLoop, isLoopAnomaly, modelString = self._parseLoopExpr(modelString[i:])	# get the loop expression
				loopStartActivities, loopEndActivities = self._convert(loopExpr, []) #build the loop subprocess
				#configure edges from current processes to end of loop processes
				for lastActivity in lastActivities:
					for loopStartActivity in loopStartActivities:
						self._addEdge(lastActivity, loopStartActivity, pLoop, isLoopAnomaly, "LOOP") #only the input edges to the loop are marked as LOOP-type
				#configure edges from end of loop back to current processes
				for lastActivity in lastActivities:
					for loopEndActivity in loopEndActivities:
						self._addEdge(loopEndActivity, lastActivity, pLoop, False, "SEQ") #loop-exit anomaly status is not considered; and the return edges are just SEQ-type
				if len(firstActivities) == 0:
					print("WARNING: firstActivities empty in loop-expr builder of _convert(). This should not occur, unless model string is not properly constrained,")
					print("such that loops must be preceded by a base activity.")
					firstActivities = [self._getActivityLabel(activity) for activity in loopStartActivities]
				i = 0 #reset to zero, since modelString is reset to remainder of string after sub-expr
				
			else:
				print("WARNING: unknown activity or operator char in model string: >"+modelString[i]+"<")
				print("Remaining model string: "+modelString)
				i += 1
		#end-while
			
		return (firstActivities,lastActivities)
		
	"""
	Given a string prefixed with a loop-expression, returns a tuple: (loopExpr, loopProbability, remainderString)
	Example: 
		input: "[ABC(F + G)HJK]:<0.6>WEY..."
		returns: ("ABC(F + G)HJK", 0.6, "WEY...")
	"""
	def _parseLoopExpr(self, modelString):
		if modelString[0] != "[":
			print("ERROR non-LOOP expr substring passed to be parsed by _parseLoopExpr(): "+modelString)
			print("Exiting")
			exit()
	
		#print("model: "+modelString)
		#find closing bracket of loop expr
		i = 0
		foundMatch = False
		unmatchedBrackets = 0
		while not foundMatch: #find span of left and right parens
			if modelString[i] == "[":
				unmatchedBrackets += 1
			if modelString[i] == "]":
				unmatchedBrackets -= 1
			if unmatchedBrackets > 0:
				i += 1
			else:
				foundMatch = True
		#post loop: i points to index of closing bracket for this expression
		
		#get the loop expression
		loopExpr = modelString[1:i]
		#get the loop probability exression: "0.2/False"
		loopProbExpr = modelString[i+2:].split(">")[0].replace("<","")
		loopProb,isAnomalous = self._parseBranchAttributes(loopProbExpr)
		#get the remainder string, after the loop expression "[ABC...]:<0.23>"
		remIndex = modelString.find(">",i) + 1
		remainder = modelString[remIndex:]
		#print("remainder: "+remainder)
		#print("loopExpr: "+loopExpr)
	
		return (loopExpr,loopProb,isAnomalous,remainder)

	"""
	Given a model string, returns all activities in the string (non-operators in expr scope). Empty branch
	'^' is retained in the modelString, and each such instance will be handled later on as a unique 'activity'.
	"""
	def _getActivities(self,modelString):
		#get the activity set from the model string
		i = 0
		exprChars = ""
		while i < len(modelString):
			#ignore subexpressions for structure attributes (enclosed in "< ... >")
			if modelString[i] == "<":
				while i < len(modelString) and modelString[i] != ">":
					i += 1
				i+=1
			if i < len(modelString) and modelString[i] in self._validActivityChars:
				exprChars += modelString[i]
			i+=1
			
		exprChars = exprChars.replace("^","")
		
		return [c for c in set(list(exprChars))]
		
	"""
	Given a model string, this parses it and converts it into an igraph graph. The graph is returned but also stored
	in the object itself.
	
	@modelString: the paraseable model string
	@showPlot: Whether or not to show the graph to the user
	"""
	def ConvertModel(self, modelString, showPlot=True):
		#create the graph
		self._graph = igraph.Graph(directed=True)
		#add the edge attributes
		self._graph.es["color"] = "black"
		self._graph.es["isAnomalous"] = False
		self._graph.es["probability"] = 1.0
		
		modelString = modelString.strip()
		#append start and end activity flags to modelString; these are just identifiers that are replaced with START and END once the recursion completes
		modelString = self._startNodeName + modelString + self._endNodeName
		
		#get the activity set from the model string; empty branch '^' is not included
		self._activities = self._getActivities(modelString)
		#add the activities as graph vertices
		self._graph.add_vertices(self._activities)
		self._graph.vs["label"] = self._activities
		#print("ACTIVITIES: "+str(self._activities))

		#recursively add nodes to the graph
		startNodes, endNodes = self._convert(modelString,[])
		startId = self._getNodeId(startNodes[0])
		self._graph.vs[startId]["name"] = "START"
		self._graph.vs[startId]["label"] = "START"
		endId = self._getNodeId(endNodes[0])
		self._graph.vs[endId]["name"] = "END"
		self._graph.vs[endId]["label"] = "END"
		#count and store the number of paths from start to end node in graph, allowing loop repeats a max of 2 times
		print("Counting num traces via path from START to END for k=2 (per Bezerra)")
		self._graph["PathCount"] = self._countPaths(self._graph, "START", "END", 2)
		#print("START: "+str(startNodes)+"  END: "+str(endNodes))

		if showPlot:
			self.Plot(self._graph)
		
		#self.Save(self._graph, saveFolder)
		#plot the graph for verification
		#self._plot( self._graph, os.path.dirname(graphPath), showPlot )
		#output the graph to some reproducible format; graphml is nice because it preserves all edge/node attributes (isAnomalous, etc.)
		#self._graph.write_graphml(graphPath)

		return self._graph

	def _getOutNeighbors(self, g, node):
		return [e.target for e in g.es[g.incident(node,mode="OUT")]]

	def _countPaths(self, g, startName, endName, k):
		#mark all the nodes per number of times traversed (max of k)
		g.vs["pathCountHits"] = 0
		#get start node
		startNode = g.vs.find(name=startName)
		#get immediate out-edge neighbors of START
		q = self._getOutNeighbors(g, startNode)
		pathct = 0

		#print("out neighbors: "+str(q))
		while len(q) > 0:
			#pop front node
			nodeId = q[0]
			node = g.vs[nodeId]
			q = q[1:]
			#get type of edge pointing to this node; note this detects if any edge pointing to node is LOOP type--unnecessary in our topology (loops only have one entrant edge), but robust
			isLoop = [e for e in g.es if e.target == nodeId][0]["type"] == "LOOP"
			#print("isloop: "+str(isLoop))
			
			#print(str(node["pathCountHits"]))
			node["pathCountHits"] += 1
			if node["name"] == endName:
				#print("++")
				pathct += 1
			#append non-loop successors, or loop successors whom we have traversed fewer than k time, to horizon
			elif not isLoop or node["pathCountHits"] < k:
				q += self._getOutNeighbors(g, node)

		#print("Pathct: "+str(pathct))
				
		return pathct

	"""
	Utility for plotting the generated graph, detecting anomalous edges and the like.
	
	@graphmlPath: Path to which graphml and png plot of graph will be saved.
	"""
	def Save(self, graph, graphmlPath, showPlot=False):
		#the sugiyama layout tends to have the best layout for a cyclic, left-to-right graph
		layout = graph.layout("sugiyama")
		#see: http://stackoverflow.com/questions/24597523/how-can-one-set-the-size-of-an-igraph-plot
		imgSavePath = graphmlPath.replace(".graphml", ".png")
		igraph.plot(graph, imgSavePath, layout = layout, bbox = (1000,1000), vertex_size=35, vertex_label_size=15)
		
		#save the graph in graphml
		graph.write_graphml(graphmlPath)

		#plot and show the graph, if desired
		if showPlot:
			self.Plot(graph)

	def Plot(self, graph):
		#the sugiyama layout tends to have the best layout for a cyclic, left-to-right graph
		layout = graph.layout("sugiyama")
		igraph.plot(graph, layout = layout, bbox = (1000,1000), vertex_size=35, vertex_label_size=15)
		
def usage():
	print("python ./ModelConverter.py [modelFile] [optional graphml output path; default is 'model.graphml'] [--quiet: optional; whether or not to show the graph]")

def main():
	if len(sys.argv) < 2:
		print("ERROR insufficient parameters passed.")
		usage()
		exit()
	ifile = open(sys.argv[1],"r")
	modelString = ifile.read(-1).strip()
	ifile.close()
	
	outputPath = "model.graphml"
	if len(sys.argv) == 3:
		outputPath= sys.argv[2]
	
	showPlot = "--quiet" not in sys.argv
	
	converter = ModelConverter()
	converter.ConvertModel(modelString,outputPath,showPlot)

if __name__ == "__main__":
	main()
