
import igraph
import copy
import sys

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
		self.activities = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0987654321"

	"""
	Looks up the nodeId (usually just its numeric index) in the igraph vs container.
	"""
	def _getNodeId(self,nodeLabel):
		for v in self.graph.vs:
			if v["name"] == nodeLabel:
				return v.index

	def _addEdge(self,v1,v2,pEdge=1.0):
		v1Id = self._getNodeId(v1)
		v2Id = self._getNodeId(v2)
		self.graph.add_edge(v1Id, v2Id,probability=pEdge)

	"""
	Given a string beginning with an AND/OR expression "(", this parses the expr arguments and operator,
	returning a tuple of (leftArg,rightArg,operator,remainder).
	
	Given: "(A | (B | C))ABC..." this function returns (A,(B|C),"|","ABC...")
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

		#grab the probability tuple "(...):<0.2,0.8>"
		j = i
		while modelString[j] != ">":
			j+=1
		#post-loop: j points to index of ">"
		probs = modelString[i+1:j].replace(">","").replace(":","").replace("<","").split(",")
		pLeft = float(probs[0])
		pRight = float(probs[1])
		print("pleft,pright: "+str(pLeft)+"  "+str(pRight))
		leftArg = modelString[1:operatorIndex]
		rightArg = modelString[operatorIndex+1:i]
		operator = modelString[operatorIndex]
		remainder = modelString[j+1:]
		print("leftArg: "+leftArg)
		print("rightArg: "+rightArg)
		print("operator: "+operator)
		print("remainder: "+remainder)
		
		return (leftArg,pLeft,rightArg,pRight,operator,remainder)

	"""
	Builds the graph up from a recursive tree according to the model-generator grammar.

	


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
				leftExpr,rightExpr,opString,remainder = _parseAndOrExpr(modelString) #returns a tuple: (leftExpr, rightExpr, operator, remainder)
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

			eli f "[" == modelString[0]:
				loopExpr, loopProb, modelString = _parseLoopExpr(modelString)	# return tuple
				loopEndActivities = _convert(loopExpr, lastActivities)
				#configure edges from end of loop back to current processes
				for lastActivity in lastActivities:
					for loopEndActivity in loopEndActivities:
						self._addEdge(loopEndActivity, lastActivity)

			return lastActivities
	"""
	"""
	The recursive expression parser. For any subprocess/expression, this returns the input and output
	activities/nodes for threading them together.
	"""
	def _convert(self,rModelString, rLastActivities):
		#save the first activity, to be returned as this subprocesses input
		firstActivities = []
		#foolish method to deep copy the recursive args
		modelString = rModelString.strip()
		lastActivities = rLastActivities + []
		
		if len(modelString) == 0:
			return ([],[])
		
		if modelString[0] in self.activities:
			firstActivities = modelString[0]
			#lastActivities = []
			i = 0
			while i < len(modelString):
				if modelString[i] in self.activities:
					#connect simple, linear activities: A->B
					for lastActivity in lastActivities:
						self._addEdge(lastActivity, modelString[i])
					lastActivities = [modelString[i]]

				elif modelString[i] == "(":
					leftExpr, pLeft, rightExpr, pRight, opString, modelString = self._parseAndOrExpr(modelString[i:])
					leftInputs, leftOutputs = self._convert(leftExpr,lastActivities)
					rightInputs, rightOutputs = self._convert(rightExpr,lastActivities)
					print("POST expr: "+modelString)
					#configure the inputs for the left branch
					for activity in leftInputs:
						for lastActivity in lastActivities:
							self._addEdge(lastActivity,activity,pLeft)

					#configure the inputs to the right branch
					for activity in rightInputs:
						for lastActivity in lastActivities:
							self._addEdge(lastActivity, activity, pRight)
					lastActivities = leftOutputs + rightOutputs
					
				elif modelString[i] == "[":
					loopExpr, pLoop, modelString = self._parseLoopExpr(modelString[i:])	# return tuple
					#print("POST parseLoopExpr: "+modelString)
					loopStartActivities, loopEndActivities = self._convert(loopExpr, lastActivities)
					#configure edges from current activities into the loop
					for lastActivity in lastActivities:
						for loopStartActivity in loopStartActivities:
							self._addEdge(lastActivity,loopStartActivity,pLoop)
					#configure edges from end of loop back to current processes
					for lastActivity in lastActivities:
						for loopEndActivity in loopEndActivities:
							self._addEdge(loopEndActivity, lastActivity,pLoop)
				else:
					print("WARNING: unknown activity or operator char in model string: "+modelString[i])
				i += 1
				#end-while
		
		#AND/OR opening expression detected; so parse its args and recurse on them
		elif "(" == modelString[0]:
			leftExpr,pLeft,rightExpr,pRight,opString,remainder = self._parseAndOrExpr(modelString) #returns a tuple: (leftExpr, rightExpr, operator, remainder)
			leftInputs, leftOutputs = self._convert(leftExpr, lastActivities) #recurse on left-expr
			rightInputs, rightOutputs = self._convert(rightExpr, lastActivities) #recurse on right-expr
			
			#configure the inputs for the left branch
			for activity in leftInputs:
				for lastActivity in lastActivities:
					self._addEdge(lastActivity,activity,pLeft)

			#configure the inputs to the right branch
			for activity in rightInputs:
				for lastActivity in lastActivities:
					self._addEdge(lastActivity, activity, pRight)			#save the outputs for the next iteration
			
			lastActivities = leftOutputs + rightOutputs
			firstActivities = leftInputs + rightInputs
			
		elif "[" == modelString[0]:
			loopExpr, pLoop, modelString = self._parseLoopExpr(modelString)	# return tuple
			loopStartActivities, loopEndActivities = self._convert(loopExpr, lastActivities)
			#configure edges from end of loop back to current processes
			for lastActivity in lastActivities:
				for loopEndActivity in loopEndActivities:
					self._addEdge(loopEndActivity, lastActivity, pLoop)
			firstActivities = loopStartActivities
			lastActivities = loopEndActivities

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
		#get the loop probability
		loopProb = float( modelString[i+2:].split(">")[0].replace("<","") )
		#get the remainder string, after the loop expression "[ABC...]:<0.23>"
		remIndex = modelString.find(">",i) + 1
		remainder = modelString[remIndex:]
		print("remainder: "+remainder)
		print("loopExpr: "+loopExpr)
	
		return (loopExpr,loopProb,remainder)

	"""
	Given a model string, this parses it and converts it into an igraph graph. The graph is returned but also stored
	in the object itself.
	"""
	def ConvertModel(self,modelString):
		self.graph = igraph.Graph(directed=True)
		
		activities = set([c for c in modelString if c in self.activities])
		self.activities = ""
		for c in activities:
			self.activities += c
		print("My activities: "+self.activities)
		
		#add the activities as graph vertices
		self.graph.add_vertices(self.activities)
		self.graph.vs["label"] = self.activities

		#recursively add nodes to the graph
		self._convert(modelString,[])
	
		igraph.plot(self.graph)
	
def usage():
	print("python ./ModelConverter.py [modelFile]")

def main():
	if len(sys.argv) < 2:
		print("ERROR insufficient parameters passed.")
		usage()
		exit()
	ifile = open(sys.argv[1],"r")
	modelString = ifile.read(-1)
	ifile.close()
	
	converter = ModelConverter()
	converter.ConvertModel(modelString)

		
if __name__ == "__main__":
	main()
	
	
	