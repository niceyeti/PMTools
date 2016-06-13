from ModelGenerator import ModelGenerator
import igraph


"""
Given a process-model string as output by ModelGenerator.py, this build a graph structure based on 
the process-model using the igraph api. The igraph api is a powerful api for building, maintaining, traversing,
and serializing graphs.

Input: a process-model string as described by ModelGenerator.py
Ouput: a directed, edge-weighted graph in graphML. Such a graph can then be transferred to any
other object for generating data.

"""

class ModelConverter(object):
	def __init__(self):
		self.graph = None
		self.operators = "()&|[]"
		self.activities = ""
	
	"""
	Looks up the nodeId (usually just its numeric index) in the igraph vs container.
	"""
	def _getNodeId(self,nodeLabel):
		for v in self.graph.vs:
			if v["name"] == nodeLabel:
				return v.id
	
	"""
	Given a string beginning with an AND/OR expression "(", this parses the expr arguments and operator,
	returning a tuple of (leftArg,rightArg,operator,remainder).
	
	Given: "(A | (B | C))ABC..." this function returns (A,(B|C),"|","ABC...")
	"""
	def _parseAndOrExpr(self,modelString):
		if modelString[0] != "(":
			print("ERROR non-AND/OR substring passed to be parsed by _parseAndOrExpr(): "+modelString)
			return []
	
		#find open/close parens of expr, and the position of the operator (& or |)
		i = 0
		operatorIndex = -1
		unmatchedParens = 1
		inScope = True #whether or not an operator we encounter is in inScope of the current expr
		while unmatchedParens > 0: #find span of left and right parens
			if modelString[i] == "(":
				unmatchedParens += 1
			if modelString[i] == ")":
				unmatchedParens -= 1
				
			if unmatchedParens > 1:
					inScope = False
			else:
					inScope = True

			if inScope and modelString[i] in self.operators:
				operatorIndex = i

			if unmatchedParens > 0:
				i += 1
		#post loop: i points to index of closing paren for this expression, operatorIndex points to index of operator
		leftArg = modelString[1:operatorIndex]
		rightArg = modelString[operatorIndex+1:i]
		operator = modelString[operatorIndex]
		remainder = modelString[i:]
	
		return (leftArg,rightArg,operator,remainder)
	
	
	"""
	Builds the graph up from a recursive tree according to the model-generator grammar.
	
	Returns: a list of nodes, to which the current node should point.
	
	"""
	def _convert(self,modelString):
		if len(modelString) == 0:
			return []
	
		#activity detected; so just recurse linearly
		if modelString[0] in self.activities:
			leftId = _getNodeId(modelString[0])
			for v in _convert(modelString[1:]):
				self.graph.add_edge((leftId,v["id"]))
			return [modelString[0]]
	
		#AND/OR opening expression detected; so parse its args and recurse on them
		if "(" == modelString[0]:
			exprTup = _andOr(modelString) #returns a tuple: (leftExpr, rightExpr, operator, remainder)
			isOr = (exprTup[2] == "|") #detect if the expression is an OR, which has probability labels
			if isOr: #parse the probablity data for each branch
				pLeft = float(exprTup[0].split(":")[1].replace("<","").replace(">",""))
				pRight = float(exprTup[1].split(":")[1].replace("<","").replace(">",""))
			
			for 
			
				
		if "[" == modelString[0]:
			exprTup = _loop(modelString)	# return tuple
			pLoop = float(exprTup[0].split(":")[1].replace("<","").replace(">","")
			
	
	"""
	Given a model string, this parses it and converts it into an igraph graph. The graph is returned but also stored
	in the object itself.
	"""
	def ConvertModel(self,modelString):
		self.graph = igraph.Graph(directed=True)
	
		#build up a list of activities
		self.activities = "^"
		for c in modelstring:
			if c not in self.operators:
				self.activities += c
		self.activities = set(self.activities) #uniquify
	
		#add the activities as graph vertices
		self.graph.add_vertices(list(self.activities))
	
		#recurively add nodes to the graph
		_convert(modelString)
	
	
	
	
	