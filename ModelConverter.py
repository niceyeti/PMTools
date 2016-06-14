from ModelGenerator import ModelGenerator
import igraph
import copy


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
			print("PARSE ERROR non-AND/OR substring passed to be parsed by _parseAndOrExpr(): "+modelString)
			print("Exiting disgracefully")
			exit()
	
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

	

	"""
	def _convert(self,outerModelString,lastOutputs):
		#silly copying, since Python's execution model does not store function param values on a true recursive frame
		modelString = copy.deepcopy(outerModelString)
		lastActivities = copy.deepcopy(lastOutputs)
		
		while len(modelString) > 0:  #modelString is recursively eaten
			#base case: current activity is just a simple linear activity transition: A->B
			if modelString[0] in self.activities:
				for lastActivity in lastActivities:
					self._addEdge(lastActivity, modelString[0])
				#update last-activities list and modelString
				lastActivities = [modelString[0]]
				modelString = modelString[1:]
				
			#AND/OR opening expression detected; so parse its args and recurse on them
			elif "(" == modelString[0]:
				leftExpr,rightExpr,opString,remainder = _parseAndOr(modelString) #returns a tuple: (leftExpr, rightExpr, operator, remainder)
				if opString == "|": #parse the probablity data for each branch
					pLeft = float(leftExpr.split(":")[1].replace("<","").replace(">",""))
					pRight = float(rightExpr[1].split(":")[1].replace("<","").replace(">",""))
				elif opString == "&": #else, this is an AND split, so assign probability 1.0 to both branches. 
					pLeft = 0.0
					pRight = 0.0
				(in1,out1) = _convert(leftExpr,lastActivities) #recurse on left-expr
				(in2,out2) = _convert(rightExpr,lastActivities) #recurse on right-expr
				
				#configure the input nodes of this subprocess
				for inputActivity in [in1 + in2]:
					for lastActivity in lastActivities:
						self._addEdge(lastActivity, inputActivity)
				#save the outputs for the next iteration
				lastActivities = out1 + out2
				modelString = remainder

			elif "[" == modelString[0]:
				loopExpr, loopProb, modelString = _parseLoopExpr(modelString)	# return tuple
				loopEndActivities = _convert(loopExpr, lastActivities)
				#configure edges from end of loop back to current processes
				for lastActivity in lastActivities:
					for loopEndActivity in loopEndActivities:
						self._addEdge(loopEndActivity, lastActivity)

			return lastActivities
	
	"""
	Given a string prefixed with a loop-expression, returns a tuple: (loopExpr, loopProbability, remainderString)
	Example: 
		input: "[ABC(F + G)HJK]:<0.6>WEY..."
		returns: ("ABC(F + G)HJK", 0.6, "WEY...")
	"""
	def _parseLoopExpr(self, modelString)
		if modelString[0] != "[":
			print("ERROR non-LOOP expr substring passed to be parsed by _parseLoopExpr(): "+modelString)
			print("Exiting")
			exit()
	
		#find closing bracket of loop expr
		i = 0
		unmatchedBrackets = 1
		while unmatchedBrackets > 0: #find span of left and right parens
			if modelString[i] == "[":
				unmatchedBrackets += 1
			if modelString[i] == "]":
				unmatchedBrackets -= 1
			if unmatchedBrackets > 0:
				i += 1
		#post loop: i points to index of closing bracket for this expression
		
		#get the loop expression
		loopExpr = modelString[1:i]
		#get the loop probability
		loopProb = float( modelString[i+2:].split(">")[0].replace("<","") )
		#get the remainder string, after the loop expression "[ABC...]:<0.23>"
		remainder = modelString[modelString.find(begin=i, ">")+1:]
	
		return (loopExpr,loopProb,remainder)

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
	
	
	
	
	