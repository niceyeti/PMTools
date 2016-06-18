
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
		self.validActivityChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0987654321_^"

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
		print("MODEL STRING: "+modelString)
		print("REMAINDER: "+modelString[i:])
		
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
		print("pleft,pright: "+str(pLeft)+"  "+str(pRight))
		print("leftArg: "+leftArg)
		print("rightArg: "+rightArg)
		print("operator: "+operator)
		print("remainder: "+remainder)
		
		return (leftArg,pLeft,isLeftAnomaly,rightArg,pRight,isRightAnomaly,operator,remainder)

	"""
	Given branch attributes, returns probability and isAnomaly as a tuple.
	Example: "0.2/False" returns a tuple (0.2,False)
	"""
	def _parseBranchAttributes(self,expr):
		pBranch = float(expr.split("/")[0])
		isAnomaly = expr.split("/")[1] == "True"
		return pBranch,isAnomaly
		
	"""
	The recursive expression parser. For any subprocess/expression, this returns the input and output
	activities/nodes for threading them together.
	"""
	def _convert(self,rModelString, rLastActivities):
	
		#base case
		if len(rModelString) == 0:
			return ([],[])
	
		#save the first activity, to be returned as this subprocess' input
		firstActivities = []
		#foolish method to deep copy the recursive args
		modelString = rModelString + ""
		lastActivities = rLastActivities + []
		
		#print("CONVERT modelstr: "+modelString)
		
		if modelString[0] in self.activities:
			firstActivities = [modelString[0]]
			#lastActivities = []
			i = 0
			while i < len(modelString):
				if modelString[i] in self.activities:
					#connect simple, linear activities: A->B
					for lastActivity in lastActivities:
						self._addEdge(lastActivity, modelString[i])
					lastActivities = [modelString[i]]
					i += 1
				elif modelString[i] == "(":
					leftExpr, pLeft, isLeftAnomaly, rightExpr, pRight, isRightAnomaly, opString, modelString = self._parseAndOrExpr(modelString[i:])
					leftInputs, leftOutputs = self._convert(leftExpr,lastActivities)
					rightInputs, rightOutputs = self._convert(rightExpr,lastActivities)
					#print("POST expr: "+modelString)
					""" #done inside _convert
					#configure the inputs for the left branch
					for activity in leftInputs:
						for lastActivity in lastActivities:
							self._addEdge(lastActivity,activity,pLeft)
					#configure the inputs to the right branch
					for activity in rightInputs:
						for lastActivity in lastActivities:
							self._addEdge(lastActivity, activity, pRight)
					"""
					lastActivities = leftOutputs + rightOutputs
					#print("LAST: "+str(lastActivities))
					i = 0 #reset to zero, since modelString is reset to remainder of string after sub-expr
				elif modelString[i] == "[":
					loopExpr, pLoop, isLoopAnomaly, modelString = self._parseLoopExpr(modelString[i:])	# return tuple
					#print("POST parseLoopExpr: "+modelString)
					loopStartActivities, loopEndActivities = self._convert(loopExpr, lastActivities)
					"""
					#configure edges from current activities into the loop
					for lastActivity in lastActivities:
						for loopStartActivity in loopStartActivities:
							self._addEdge(lastActivity,loopStartActivity,pLoop)
					"""
					#configure edges from end of loop back to current processes
					for lastActivity in lastActivities:
						for loopEndActivity in loopEndActivities:
							self._addEdge(loopEndActivity, lastActivity,pLoop)
					i = 0 #reset to zero, since modelString is reset to remainder of string after sub-expr
				else:
					print("WARNING: unknown activity or operator char in model string: "+modelString[i])
					print("Remaining model string: "+modelString)
					i += 1
			#end-while
		
		#AND/OR opening expression detected; so parse its args and recurse on them
		elif "(" == modelString[0]:
			leftExpr,pLeft,isLeftAnomaly,rightExpr,pRight,isRightAnomaly,opString,remainder = self._parseAndOrExpr(modelString) #returns a tuple: (leftExpr, rightExpr, operator, remainder)
			leftInputs, leftOutputs = self._convert(leftExpr, lastActivities) #recurse on left-expr
			print("Left in/out: "+str(leftInputs)+"  "+str(leftOutputs))
			rightInputs, rightOutputs = self._convert(rightExpr, lastActivities) #recurse on right-expr
			print("Right in/out: "+str(rightInputs)+"  "+str(rightOutputs))
			#configure the inputs for the left branch
			for activity in leftInputs:
				for lastActivity in lastActivities:
					self._addEdge(lastActivity,activity,pLeft)
			#configure the inputs to the right branch
			for activity in rightInputs:
				for lastActivity in lastActivities:
					self._addEdge(lastActivity, activity, pRight)	#save the outputs for the next iteration
			firstActivities = leftInputs + rightInputs
			lastActivities = leftOutputs + rightOutputs
			print("FIRST ACTS: "+str(firstActivities))
			print("LAST ACTS: "+str(lastActivities))
			
		elif "[" == modelString[0]:
			loopExpr, pLoop, isLoopAnomaly, modelString = self._parseLoopExpr(modelString)	# return tuple
			loopStartActivities, loopEndActivities = self._convert(loopExpr, lastActivities)
			#configure edges from end of loop back to current processes
			for lastActivity in lastActivities:
				for loopStartActivity in loopStartActivities:
					self._addEdge(lastActivity,loopStartActivity,pLoop)
			#configure edges from end of loop back to current processes
			for lastActivity in lastActivities:
				for loopEndActivity in loopEndActivities:
					self._addEdge(loopEndActivity, lastActivity,pLoop)
			firstActivities = loopStartActivities
			lastActivities = loopEndActivities
			print("LOOP FIRST ACTS: "+str(firstActivities))
			print("LOOP LAST ACTS: "+str(lastActivities))
			
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
		print("remainder: "+remainder)
		print("loopExpr: "+loopExpr)
	
		return (loopExpr,loopProb,isAnomalous,remainder)

	"""
	Given a model string, returns all activities in the string (non-operators in expr scope).
	"""
	def _getActivities(self,modelString):
		#get the activity set from the model string
		i = 0
		exprChars = ""
		while i < len(modelString):
			if modelString[i] == "<":
				while i < len(modelString) and modelString[i] != ">":
					i += 1
				i+=1
			if i < len(modelString) and modelString[i] in self.validActivityChars:
				exprChars += modelString[i]
			i+=1
		
		activities = ""
		for c in set(list(exprChars)):
			activities += c
		print("My activities: "+activities)		
	
		return [c for c in activities]
		
	"""
	Given a model string, this parses it and converts it into an igraph graph. The graph is returned but also stored
	in the object itself.
	"""
	def ConvertModel(self,modelString):
		self.graph = igraph.Graph(directed=True)
		
		#get the activity set from the model string
		self.activities = self._getActivities(modelString)
		self.activities += ["START","END"]
		#add the activities as graph vertices
		self.graph.add_vertices(self.activities)
		self.graph.vs["label"] = self.activities

		#recursively add nodes to the graph
		startActivities, endActivities = self._convert(modelString,[])
		for activity in startActivities:
			self._addEdge("START",activity)
		for activity in endActivities:
			self._addEdge(activity,"END")	
		layout = self.graph.layout("sugiyama")
		#layout = self.graph.layout("kk") #options: kk, fr, tree, rt
		#seee: http://stackoverflow.com/questions/24597523/how-can-one-set-the-size-of-an-igraph-plot
		igraph.plot(self.graph, layout=layout)
	
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
	
	
	