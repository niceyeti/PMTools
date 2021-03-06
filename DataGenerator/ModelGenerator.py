import sys
import math
import random
import igraph
from ModelConverter import ModelConverter

"""
Randomly generates process models according to Algorithm 4, in Bezerra's paper on process-mining anomaly detection.
Using that algorithm, this script randomly generates process models which can subsequently be used to generate
trace data based on the probabilities embedded in the models themselves.

Hence, this model-generator produces models in a probabilistic fashion as Bezerra's work, but also embeds probabilities
in the edges of the workflows. These embedded probabilities are then used to generate traces. Thus, this script
can implement Bezerra's generation method in the base-case, but can extend it by incorporating probability data
into workflow edges.

Input:  print("python ./ModelGenerator -n=(some +integer <= 62) [-config=configPath] [-file=(path to output file)]")

Output: A graph in graphML format, with probabilistic edges.

A is a subproc, which may be an activity or any composition of the following.

ANDs are encased in ()
OR is encased by {}
LOOP is denoted by []

An OR has two associated probabilities: {A:<0.1>,B:<0.9>}
A loop has one-stated associated probability for taking the loop: [A]:<0.3>. The probability of breaking the loop is therefore just 1 - 0.3 = 0.7.


Note that only OR and LOOP may have any associated probability; AND-splits require both edges to be traversed.

ABC(E+F)[AB]:<>

Any structure with a ":<>" parameter is tagged with "Anomaly=True/False", such as (ABC|DEF):<0.2/False,0.8/True>

This component only generates models and embeds probabilities on each branch, using a regular expression, parsing embedded
parameters from a .config file. For the embedded parameters, a value less than zero can be used as a placeholder signal value,
such as to indicate that params will be determined later. This allows generating expressions, then embedding different values
of the same parameter into the same model and generating traces for each such value, for experimental testing.



Optional: --loopUntilKAnomalies. If passed, the model generator will generate models until one is found with k (the -a parameter)
anomalies. This is done by searching over the pAnom parameters AnomalousLoopProb/AnomalousOrBranchProb by increasing/decreasing
both of these if a generated model is under/over the target number of anomalies. If passed, then @MaxAnomalousEdges is ignored.
The loop search is basic, generating a bunch of models and taking the max number of anomalies, while less than @MaxAnomalousEdges,
then manually adds random anomalies to the process graph from ModelConverter.

"""

class ModelGenerator(object):
	def __init__(self, configPath):
		#activity dictionary; let activities be defined by simple symbols in Sigma, each with some label
		#self.activities = {'A':"PullLever",'B':"PushButton",'C':"SpinWheel",'D':"TwistKnob",'E':"PullSpring",'F':"TootWhistle",'G':"RingBell",'H':"TapGauge",'I':"WipeForehead",'J':"ReadGauge",'K':"SmellSmoke",'L':"TapKeys",'M':"PushPedal"}
		self._remainingActivities = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
		self._activities = self._remainingActivities.strip() # a pseudo deep copy
		self._model = ""
		self._abnormalOrProbRange = (-1.0,-1.0)
		self._normalOrProbRange = (-1.0,-1.0)
		self._abnormalLoopProbRange = (-1.0,-1.0)
		self._normalLoopProbRange = (-1.0,-1.0)
		self._anomalousOrBranchProb = 0.0   #the probability of *producing* an anomalous OR branch, whose parameters will be set to by self._abnormalOrProbRange
		self._anomalousLoopProb=0.0   #the probability of *producing* an anomalous LOOP, whose parameters will be set to by self._abnormalLoopProbRange
		self._anomalyCount = 0
		self._requiredAnomalies = 999
		self._minShortestPathLength = 9999
		self._parseConfig(configPath)
		self._loopUntilKAnomalies = False
		self._modelConverter = ModelConverter()

	"""
	Parses in the parameters/vals of the config file. All are required.
	Note no error checking is done on the file's existence or its format.
	"""
	def _parseConfig(self,configPath):
		self._anomalousOrBranchProb = 0.0
		self._anomalousLoopProb=0.0
		self._abnormalOrProbRange = (-1.0,-1.0)
		self._normalOrProbRange = (-1.0,-1.0)
		self._abnormalLoopProbRange = (-1.0,-1.0)
		self._normalLoopProbRange = (-1.0,-1.0)
		self._requiredAnomalies = -1
		self._maxAnomalousEdges = 9999
		self._minShortestPathLength = 9999
	
		config = open(configPath,"r")
		for line in config.readlines():
			line = line.split("#")[0]
		
			if "AnomalousLoopProb=" in line:
				self._anomalousLoopProb = float(line.split("=")[1])
			if "AnomalousOrBranchProb=" in line:
				self._anomalousOrBranchProb = float(line.split("=")[1])
			if "AbnormalOrProbRange=" in line:
				vals = line.split("=")[1].split(",")
				self._abnormalOrProbRange = (float(vals[0]),float(vals[1]))
			if "NormalOrProbRange=" in line:
				vals = line.split("=")[1].split(",")
				self._normalOrProbRange = (float(vals[0]),float(vals[1]))
			if "AbnormalLoopProbRange=" in line:
				vals = line.split("=")[1].split(",")
				self._abnormalLoopProbRange = (float(vals[0]),float(vals[1]))
			if "NormalLoopProbRange=" in line:
				vals = line.split("=")[1].split(",")
				self._normalLoopProbRange = (float(vals[0]),float(vals[1]))
			if "NumAnomalies=" in line:
				self._requiredAnomalies = int(line.split("=")[1])
			if "MaxAnomalousEdges=" in line:
				self._maxAnomalousEdges = int(line.split("=")[1])
			if "MinShortestPathLength=" in line:
				self._minShortestPathLength = int(line.split("=")[1])
				
		print("MIN PATH LENGTH: "+str(self._minShortestPathLength))
		if self._requiredAnomalies < 0:
			print("ERROR config did not contain NumAnomalies")
		if self._abnormalOrProbRange[0] < 0.0:
			print("ERROR config did not contain AbnormalOrProbRange")
		if self._abnormalLoopProbRange[0] < 0.0:
			print("ERROR config did not contain AbnormalLoopProbRange")
			
		#These checks are now obsolete, since -1.0 can be used a a placeholder/signal value for these parameters
		#if self._normalLoopProbRange[0] < 0.0:
		#	print("ERROR config did not contain NormalLoopProbRange")
		#if self._normalOrProbRange[0] < 0.0:
		#	print("ERROR config did not contain NormalOrProbRange")

	"""
	Returns a random activity from the activity set. The activity is then deleted from the available activity set, so they may only be used once.
	"""
	def _generateRandomActivity(self):
		if len(self._remainingActivities) == 0:
			alpha = ""
		elif len(self._remainingActivities) == 1: #this and the prior conditional are both degenerate cases
			alpha = self._remainingActivities[0]
			self._remainingActivities = ""
		else:
			randomIndex = random.randint(0,len(self._remainingActivities)-1) #symbols remaining, so randomly choose one
			alpha = self._remainingActivities[randomIndex]
			#delete the old activity, preventing them from being repeated
			self._remainingActivities = self._remainingActivities.replace(alpha,"")

		return alpha

	def GetModel(self):
		return self._model
		
	"""
	Implements the rndSplit() function, directly from Bezerra. Generates two numbers in Z+,
	such that n1 + n2 = n
	"""
	def _rndSplit(self,n):
		if n <= 1:
			print("WARNING: ERROR, n <= 1 in _rndSplit(). n must be >= 2, s.t. n1, n2 can both be positive.")
			return 0,1
		if n== 2: #randint() will throw an exception for this degenerate case, so return 1,1 directly
			return 1,1
		else:
			r = random.randint(1,n)
			return r,n-r
		
	"""
	Randomly chooses and returns a probability in the range low-hi, where low < hi and low,hi = [0.0-1.0)
	
	@low: float in range [0.0-1.0)
	@hi: float in range [0.0-1.0)
	"""
	def _getRandomProb(self,low,hi):
		if low > hi:
			print("ERROR low > hi in _getRandomProb, swapping")
			t = low
			low = hi
			hi = t
		if low < 0.0 or low >= 1.0:
			print("low range error for "+str(low)+" in _getRandomProb()")
			low = 0.5
			hi = 0.5
		if hi < 0.0 or hi >= 1.0:
			print("hi range error for "+str(hi)+" in _getRandomProb()")
			low = 0.5
			hi = 0.5

		n = random.randint(int(low*1000), int(hi*1000))
		return float(n) / 1000.0
			
	"""
	Returns a probability for a given OR branch, under 'normal' (not suspicious or anomalous) conditions.
	'Normal' does not refer to the probability distribution, only to 'normal' process execution.
	
	Normal here is therefore some just bounded somehow to higher entropy values, such as lying between 0.2 and 0.8
	"""
	def _getNormalOrProb(self):
		
		#return signal values, if either in range is a signal (a value less than zero)
		if self._normalOrProbRange[0] < 0:
			return self._normalOrProbRange[0]
		if self._normalOrProbRange[1] < 0:
			return self._normalOrProbRange[1]
	
		#generate a random probability number in a range
		return self._getRandomProb(self._normalOrProbRange[0], self._normalOrProbRange[1] )

	"""
	Inverse of previous. Returns a randomly-chosen non-zero probability bounded to some very low, outlier range, such as 0.001-0.1.
	"""
	def _getAbnormalOrProb(self):
		return self._getRandomProb( self._abnormalOrProbRange[0], self._abnormalOrProbRange[1] )
		
	"""
	Returns the probability of traversing some sub-loop, under normal (non-anomalous) behavioral conditions for the model. 
	
	Return signal value from prob ranges if either is a signal (Less than zero)
	"""
	def _getNormalLoopProb(self):
		if self._normalLoopProbRange[0] < 0:
			return self._normalLoopProbRange[0]
		if self._normalLoopProbRange[1] < 0:
			return self._normalLoopProbRange[1]
	
		return self._getRandomProb( self._normalLoopProbRange[0], self._normalLoopProbRange[1] )
		
	def _getAbnormalLoopProb(self):
		return self._getRandomProb( self._abnormalLoopProbRange[0], self._abnormalLoopProbRange[1] )

	"""
	Builds and returns a probability expression string, given a probability and whether or not this is an anomalous event.
	
	HACK 10/23/17: If p is
	
	
	Given: 0.2, True, returns "0.2/True"
	"""
	def _buildProbExpr(self,p,isAnomalous):
		return str(p)+"/"+str(isAnomalous)
		
	###### The grammar rules. Note the ones that are always prepended with a non-empty activity, as a requirement.
	"""
	AND is the simplest, creating two branches, both of which shall be taken so there are no associated probs, and neither branch may be empty.
	AND must be followed by some activity and not an AND, OR, or LOOP, so some random activity is appended.
	"""
	def _and(self,n1,n2):
		return "("+self._generateRandomActivity()+self._createModel(n1-1)+"&"+self._generateRandomActivity()+self._createModel(n2-1)+")"+self._generateRandomActivity()
		
	"""
	Composes a basic sequence of subprocesse.
	
	@preventLoop: Whether or not to prevent a loop from starting at the left subprocess. This is a structural constraint imposed at certain
	points in the model generation.
	"""
	def _seq(self,n1,n2,preventLoop=False):
		#print("seq n1/n2: "+str(n1)+" "+str(n2))
		#print("preventLoop: "+str(preventLoop))
		s = self._createModel(n1,preventLoop)+self._createModel(n2)
		#print("s: "+s)
		return s #elf._createModel(n1,preventLoop)+self._createModel(n2)

	"""
	OR has a few subtle constraints. We cannot allow both branches to be empty, and neither may start with
	a loop or consist only of a loop.
	
	@n1: approximate number of subprocesses to create on left branch
	@n2: approximate number of subprocesses to create on right branch; if 0, make an empty branch
	"""
	def _or(self,n1,n2):
		#first, determine whether or not a branch should be anomalous, and assign branch probabilities
		isLeftBranchAnomalous = False
		isRightBranchAnomalous = False
		
		#declare an anomalous branch with probability self._anomalousOrBranchProb
		if (float(random.randint(1,100)) / 100.0) <= self._anomalousOrBranchProb and self._anomalyCount < self._requiredAnomalies:
			self._anomalyCount += 1
			#flip a coin to choose the anomalous branch
			if random.randint(1,2) % 2 == 0:
				isLeftBranchAnomalous=True
			else:
				isRightBranchAnomalous = True

		if not (isLeftBranchAnomalous or isRightBranchAnomalous):
			p = self._getNormalOrProb()
			#p may be a signal value, such as -1.0, allowing client to insert/vary these parameters later; this handles that logic
			if p > 0:
				leftProb = p
				rightProb = 1.0-p
			else:
				leftProb = p
				rightProb = p
			#print("LEFT: "+str(leftProb))
			#print("RIGHT: "+str(rightProb))
			leftProbExpr = self._buildProbExpr(leftProb, isLeftBranchAnomalous)
			rightProbExpr = self._buildProbExpr(rightProb, isRightBranchAnomalous)
		else:
			p = self._getAbnormalOrProb()
			if isRightBranchAnomalous:
				 p = 1.0 - p
			leftProbExpr = self._buildProbExpr(p, isLeftBranchAnomalous)
			rightProbExpr = self._buildProbExpr(1.0 - p, isRightBranchAnomalous)
		
		#leftProbExpr = self._buildProbExpr(leftProbExpr, isLeftBranchAnomalous)
		#rightProbExpr = self._buildProbExpr(rightProbExpr, isRightBranchAnomalous)
		probExpr = ":<"+leftProbExpr+","+rightProbExpr+">"
		
		if n2 > 0:
			#NOTE both branches are prepended with some concrete activity, to constraint models to binary branching
			orExpr = "("+self._generateRandomActivity()+self._createModel(n1-1)+"|" +self._generateRandomActivity()+self._createModel(n2,True)+")"+probExpr
		else:
			#note only the left branch is prepended with an activity; this is done to guarantee at least one branch has a concrete activity, preventing branches both of which are empty
			orExpr = "("+self._generateRandomActivity()+self._createModel(n1-1)+"|^)"+probExpr
			
		return orExpr
		
	def _loop(self,n1,n2):
		### TODO As for _or(), define when/how to declare anomalous loops, and what probs to assign them
		isAnomalousLoop=False
		if (float(random.randint(1,100)) / 100.0) < self._anomalousLoopProb and self._anomalyCount < self._requiredAnomalies:
			isAnomalousLoop = True
			self._anomalyCount += 1
		### End of TODO
	
		#NOTE: This function handles the case if p is a signal value, since 1.0-p isn't required for loops, as it is for _or()
		if isAnomalousLoop:
			p = self._getAbnormalLoopProb()
		else:
			p = self._getNormalLoopProb()
		probExpr = ":<"+self._buildProbExpr(p,isAnomalousLoop)+">"
		
		#Note the shoe-horned activity in the LOOP construct, to force there to be at least one activity in a loop
		return "["+self._generateRandomActivity()+self._seq(n1,n2,True)+"]"+probExpr #preventLoop=True prevents invalid double loops: [[AB]GHFJ]
	####### End of the grammar rules

	"""
	Resets the object state such that we're ready to create a fresh model
	"""
	def _reset(self):
		self._model = ""
		self._remainingActivities = self._activities.strip() #python pseudo deep copy
		self._anomalyCount = 0
	
	"""
	Just the outer driver for the recursive calls. Note that models are generated until one meets the num-anomalies requirement.
	An alternative is to generate models with LOOP and OR constructs, and then to flip their anomaly status to True, but the lazy way
	here is just clearer and easier, despite being less efficient.

	@n: number of activities
	@a: num anomalies to generate with model
	@graphmlPath: Relative path of current execution context to which graphml and graph .png will be saved
	@loopUntilKAnomalies: boolean, whether or not to generate models with 
	"""
	def CreateModel(self, n, a, graphmlPath, showPlot, loopUntilKAnomalies):
		if a > 3:
			print("WARNING generating "+str(a)+" anomalies, or more than about 3, may take too long for generator to terminate for low-probability anomalies")
			
		self._loopUntilKAnomalies = loopUntilKAnomalies
			
		#while invalid models are generated, or models without enough anomalies, create and test a new one
		isValidModel = False
		while not isValidModel:
			self._reset()
			self._model = self._createModel(n, preventLoop=True) #On the first call preventLoop is set, since the outermost expr as a loop make no sense
			#print('Before post-processing, model is: \n'+self._model)
			self._postProcessing() # a bandaid
			isValidModelStr = self._isValidModelStr(a) and self._isBezerraValidModelStr(self._model)
			#print(self._model)
			if isValidModelStr:
				#preliminary checks passed; so build the in-memory graph, and then check graph validation metrics
				self._graphicalModel = self._modelConverter.ConvertModel(self._model, False)
				if self._loopUntilKAnomalies: #The model string is verified to include at least 4 anomalies, but more than that need to be added manually to the graph
					isValidModel = self._addAnomalies(a)

				self._pathCount = self._graphicalModel["PathCount"]
				isValidModel = isValidModel and self._isBezerraValidModel(self._graphicalModel) and self._meetsAnomalyRequirements(self._graphicalModel) and self._meetsMinPathLengthRequirements(self._graphicalModel)
				if isValidModel:
					#only show valid model
					print("Model anomalous edges: "+str(self._graphicalModel["numAnomalousEdges"]))
					print("Model shortest path length from START to END: "+str(self._graphicalModel.get_shortest_paths("START",to="END",mode="OUT",output='vpath')[0]))
					self._modelConverter.Save(self._graphicalModel, graphmlPath, showPlot)
				else:
					print("INVALID graphical model")
			else:
				print("INVALID MODEL STR")

		return self._graphicalModel
		
	"""
	Given a graphical model has been built, and @numAnomalies, the required number of anomalies,
	this adds more anomalies manually until the model is satisfactory.
	
	@numAnomalies: Exact number of anomalies required of the model; could be 
	Returns: True if all additional anomalies could be added to exact number required, false otherwise.
	"""
	def _addAnomalies(self, numAnomalies):
		print("Adding anomalies to model...")
	
		if self._anomalyCount > numAnomalies: #too many anomalies already; they cannot be removed, so toss this model and regenerate
			print("ERROR anomaly count already too high: "+str(self._anomalyCount)+"    "+str(numAnomalies))
			return False

		#if self._countNonAnomalousEdges() < (numAnomalies - self._anomalyCount):
		#	return False #not enough splittable edges remaining to add anomalies too
		i = 1
		while self._anomalyCount < numAnomalies:
			if not self._addAnomaly():
				print("ERROR: could not add anomaly "+str(i)+"     aCount="+str(self._anomalyCount)+"     "+str(numAnomalies))
				return False
			else:
				self._anomalyCount += 1
				i += 1
				
		return True
		
	#Vertex is treated as anomalous if no non-anomalous edge points to it
	def _isAnomalousVertex(self, vId):
		return not any([not edge["isAnomalous"] for edge in self._graphicalModel.es.select(_target=vId)])
		#anomalousTargets = set([edge.target for edge in self._graphicalModel.es if edge["isAnomalous"]])
		#regularTargets =  set([edge.target for edge in self._graphicalModel.es if not edge["isAnomalous"]])
		#return vId in anomalousTargets and vId not in regularTargets
		
	#Utility for adding anomalies: returns a vertex with no incoming edges marked anomalous. I originally
	#required outdegree==1, but this constraint seems needless. The constraints are that the node is
	#not adjacent to END, such that there is one intervening node to jump over and join back with for branches.
	#The node must also not contain "^" indicating it is a null transition node.
	#Returns: a non-anomalous vertex, or None if none remaining.
	def _getNonAnomalousVertex(self):
		#build non-anomalous vertices: not anomalous and not END or within one-step of END
		prohibitedNodes = set([self._graphicalModel.vs[index]["name"] for index in self._graphicalModel.neighbors("END",mode="in")])
		prohibitedNodes.add("END")
		prohibitedNodes.add("START")
		vertices = [v.index for v in self._graphicalModel.vs if not self._isAnomalousVertex(v.index) and v["name"] not in prohibitedNodes and "^" not in v["name"]]

		if len(vertices) == 0:
			return None

		return vertices[ random.randint(0,len(vertices)-1) ]
	
	def _getDownstreamVertices(self, vId, visited, radius):
		if radius <= 0:
			return

		for neighborId in self._graphicalModel.neighbors(vId, mode="out"):
			if neighborId not in visited:
				visited.add(neighborId)
				self._getDownstreamVertices(neighborId, visited, radius-1)

	#Searches a random vertex downstream of (but not adjacent to) some vertex v. @visited stores downstream nodes. @radius controls search-depth bound.
	#Returns None if no vertex found
	def _getRandomDownstreamVertex(self, vId):
		vertices = set()
		neighbors = self._graphicalModel.neighbors(vId, mode="out")
		self._getDownstreamVertices(vId, vertices, 5)
		vertices = [vId for vId in vertices if vId not in neighbors]

		if len(vertices) == 0:
			return None
		
		return vertices[random.randint(0,len(vertices)-1)]
		
	#Essentially, a deletion anomaly
	def _addNullTransitionAnomaly(self):
		success = False
		#get a vertex to which an anomaly can be affixed
		vId = self._getNonAnomalousVertex()
		if vId is not None:
			#get a downstream vertex at which to join back
			downstreamId = self._getRandomDownstreamVertex(vId)
			if downstreamId is not None:
				#add the edge between these two vertices
				self._addEdge(vId, downstreamId, 0.05, True, False, "OR", "orange")
				#self._graphicalModel.add_edge(source=vId, target=downstreamId)
				self._normalizeOutEdges(vId)
				success = True
				
		return success

	def _getNewVertex(self):
		vertex = None
		vnames = [v["name"] for v in self._graphicalModel.vs if v["name"].lower() != "start"]
		newName = None
		for c in self._remainingActivities:
			if c not in vnames:
				newName = c
				break
				
		if newName is not None:
			self._remainingActivities = self._remainingActivities.replace(newName,"")
			self._graphicalModel.add_vertex(newName)
			vertex = [v for v in self._graphicalModel.vs if v["name"] == newName][0]
			vertex["label"] = vertex["name"]
			vertex["pathCountHits"] = 0 #meaningless at this point in data generation
		
		return vertex

	#This utility is for generating a new vertex with an existing vertex label. This is so that
	#we can add anomalous behavior to the model, but constrain the exit conditions when we reach
	#the node, which would not be possible if we simply selected the node itself.
	def _cloneExistingVertex(self):
		vertex = None
		vnames = [v["name"] for v in self._graphicalModel.vs if v["name"].lower() != "start"]
		clonedName = vnames[random.randint(0,len(vnames)-1)]+"_CLONE" #adding '_CLONE' is just a temporary handle for getting the vertex after adding it
		self._graphicalModel.add_vertex(clonedName)
		vertex = [v for v in self._graphicalModel.vs if v["name"] == clonedName][0]
		vertex["name"] = vertex["name"].replace("_CLONE","") #remove _CLONE temporary handle
		vertex["label"] = vertex["name"]
		vertex["pathCountHits"] = 0 #meaningless at this point in data generation
		
		return vertex
		
	def _normalizeOutEdges(self, vId):
		outEdges = [edge for edge in self._graphicalModel.es if edge.source == vId]
		z = float(sum([edge["probability"] for edge in outEdges]))
		for edge in outEdges:
			edge["probability"] = float(edge["probability"]) / z

	def _addEdge(self, srcVertex, destVertex, prob, isAnomalous, isVisited, edgeType, color):
		self._graphicalModel.add_edge(source=srcVertex, target=destVertex)
		edge = self._graphicalModel.es.select(_source=srcVertex, _target=destVertex)
		edge["probability"] = prob
		edge["visited"] = isVisited
		edge["color"] = color
		edge["type"] = edgeType
		edge["isAnomalous"] = isAnomalous

	def _addLoopAnomaly(self):
		success = False
		#get a vertex to which an anomaly can be affixed
		vId = self._getNonAnomalousVertex()
		if vId is not None:
			#get a new vertex for the additional loop
			vertex = self._getNewVertex()
			if vertex is not None:
				#add the edges creating the OR structure, decorating the edge attributes as well: ['visited', 'color', 'type', 'isAnomalous', 'probability']
				self._addEdge(vId, vertex.index, 0.05, True, False, "LOOP", "orange")
				#Normalize the probs of this node
				self._normalizeOutEdges(vId)
				#add the exit edge, which rejoins the model somewhere random downstream
				self._addEdge(vertex.index, vId, 1.0, True, False, "SEQ", "orange")
				success = True

		return success

	"""
	Null transitions and loops are fairly straightforward to insert. OR anomalies require a little more
	insight. With probability 0.5, the OR branch will branch to a new vertex label and return to the model
	somewhere downstream; this is an insertion anomaly.
	But to encompass substitution anomalies, we must transition to a new vertex that has an existing vertex
	label from the model. There is a very low probability that the selected vertex could be the same as the model
	behavior bypassed by the OR branch, but this will almost never occur. A NEW VERTEX IS ADDED TO THE MODEL
	but with an existing label/vertex name; this is just an important implementation note, since vertices are
	no longer unique by name/label. The reason we cant link to some randomly selected vertex in the model, is that
	the OR branch must return after reaching this node; but the data generator is a one-step decision process, so in most
	cases if the anomalous branch was executed (taking us to an existing model node), then from that regular node we would
	do regular stuff, and not return via the anomalous branch as desired.
	"""
	def _addOrAnomaly(self):
		success = False
		#get a vertex to which an anomaly can be affixed
		vId = self._getNonAnomalousVertex()
		if vId is not None:
			#get a downstream vertex at which to join back
			downstreamId = self._getRandomDownstreamVertex(vId)
			if downstreamId is not None:
				#with probability 0.5, get a new vertex for the OR branch (an insertion anomaly)
				if random.randint(0,99) < 50:
					vertex = self._getNewVertex()
				#else select an existing vertex name at random, and link to a new vertex with that label.
				else:
					vertex = self._cloneExistingVertex()

				if vertex is not None:
					#add the edges creating the OR structure, decorating the edge attributes as well: ['visited', 'color', 'type', 'isAnomalous', 'probability']
					self._addEdge(vId, vertex.index, 0.05, True, False, "OR", "orange")
					#Normalize the probs of this node
					self._normalizeOutEdges(vId)
					#add the exit edge, which rejoins the model somewhere random downstream
					self._addEdge(vertex.index, downstreamId, 1.0, True, False, "SEQ", "orange")
					success = True

		return success

	"""
	Utility for adding a single anomaly manually.
	
	This is the most important function for the experiment testing multiple anomalies.
	Anomalies are added by finding edges with 1.0 probability, indicating they can be split.
	
	The anomalies are chosen as: OR, LOOP with equal probability. LOOP cannot contain null
	edges, but OR can with probability 0.25, effectively giving deletion behavior (bypassing model components).
	
	NOTE: This was written such that this function should never return False, or I've made a logical error, or perhaps
	a model has some poor structure or other. Keep it this way: try to ensure this always succeeds except for rare exceptions.
	
	Returns: False if an anomaly could not be added to the current graphical model.
	"""
	def _addAnomaly(self):
		randInt = random.randint(0,98) #randint includes parameter endpoints (a,b)
		if randInt < 32: #add OR anomaly consisting of a null transition (deletion anomaly)
			success = self._addNullTransitionAnomaly()
		elif randInt < 65: #add LOOP anomaly
			success = self._addLoopAnomaly()
		else: #add OR with non-null activities: new (insertions) or cloned existing vertices (substitutions)
			success = self._addOrAnomaly()

		return success

	def PrintModel(self):
		print("Model:\n"+self._model)
		ct = 0
		i = 0
		leftBraces = 0
		while i < len(self._model):
			if self._model[i] == "<":
				leftBraces += 1
			if self._model[i] == ">":
				leftBraces -= 1
			if leftBraces == 0 and self._model[i] in self._activities:
				ct += 1
			i += 1

		print(str(ct)+" total activities, "+str(self._pathCount)+" unique paths, "+str(self._anomalyCount)+" anomalies, "+str(self._graphicalModel["numAnomalousEdges"])+" anomalous edges")

	"""
	Verifies a generated graph is valid under Bezerra's definition, such that the graph has at least k
	activities, p possible paths.

	Bezerra used k=9, p =10 (model capable of generating at least 10 unique traces).
	"""
	def _isBezerraValidModel(self,g):
		print("Validating model under Bezerra's requirements: pathct >= 10 and 9 <= numActivities <= 29.")
		p = g["PathCount"]
		k = len(g.vs)
		isValid = p >= 10 and k >= 9
		if not isValid:
			print("INVALID MODEL: contains too few paths, or too few activities: p="+str(p)+"    "+str(k))
		return isValid

	def _meetsAnomalyRequirements(self, g):
		if self._loopUntilKAnomalies:
			return True #checks on model are performed during anomaly addition
		else:
			return g["numAnomalousEdges"] <= self._maxAnomalousEdges
		
	def _meetsMinPathLengthRequirements(self, g):
		isValid = self._minShortestPathLength <= len(self._graphicalModel.get_shortest_paths("START",to="END",mode="OUT",output='vpath')[0])
		if not isValid:
			print("INVALID MODEL: min path length requirement not met: "+str(self._minShortestPathLength))
		return isValid

	"""
	THIS IS NOT A FULL CHECK FOR BEZERRA-VALIDITY. This only checks the model string for basic validity,
	such that we can discard trivially invalid model strings before running the converter to derive their graph. 
	As such, this only checks for a trivial lower-bound of Bezerra requirements (at least 10 different traces, 9 activities),
	and could leak model-strings which can't generate 10 or more unique traces. But we can still catch the trivial
	ones accordingly:
		-more than three of OR (|) or AND (&)
	"""
	def _isBezerraValidModelStr(self,modelStr):
		splitCt = 0
		for c in modelStr:
			if c in "&|":
				splitCt += 1
		return splitCt > 3
		
	"""
	For post-validation, checks that the model string is valid: not empty, doesn't contain null clauses and
	other bad structures.
	"""
	def _isValidModelStr(self, requiredAnomalies):
		#check for an approximate minimum valid length
		if len(self._model) < 3:
			print("ERROR model length too small: "+self._model)
			return False
			
		#check for empty expressions
		if self._model.find("(|)") >= 0 or self._model.find("()") >= 0:
			print("ERROR model contains empty OR expr: "+self._model)
			return False
		if self._model.find("(&)") >= 0 or self._model.find("()") >= 0:
			print("ERROR model contains empty AND expr: "+self._model)
			return False
		if self._model.find("[]") >= 0:
			print("ERROR model contains empty loop expr: "+self._model)
			return False

		#Check for outermost expressions that would allow direct transitions from START to FINISH: (A|^), (^|A), where 'A' is any recursive subprocess
		if self._model[0] == "(": #opening parent means model starts with an AND or OR expr: (A|A) or (A&A)
			#find the closing paren for the outermost expr
			closingIndex = self._model.rfind(")")
			#check if left expression is of the form '(^|A)' or '(^&A)'
			if self._model[0:3] in ["(^|", "(^&"]:
				print("BAD EXPR")
				return False
			#check if right expression is of the form '&^)' or '|^)'
			if self._model[closingIndex-2:closingIndex+1] in ["&^)","|^)"]:
				print("BAD EXPR")
				return False
		#check for consecutive empty transitions: ^^, but treat these as a warning
		if self._model.find("^^") >= 0:
			print("ERROR model string contains consecutive empty branches: "+self._model)

		#if not loopUntilKAnomalies, then exact match required number of anomalies
		if not self._loopUntilKAnomalies:
			isValid = self._anomalyCount == requiredAnomalies
			if not isValid:
				print("Incorrect number of anomalies: "+str(self._anomalyCount)+"  "+str(requiredAnomalies))
		#else, make sure there are max(4,requiredAnomalies) anomalous structures, and any remaining required will be added later manually
		else:
			#isValid = self._anomalyCount >= min(requiredAnomalies,4)
			isValid = True

		return isValid

	"""
	Cleans up model string after construction. Any potential errors should be fixed
	in the construction definition, not here. This is simply a bandaid for filtering and
	transforming the model.
	"""
	def _postProcessing(self):
		#Replace ^^ (consecutive empty activities) with nil
		self._model = self._model.replace("^^","")
		
		if len(self._model) > 0:
			#Removes empty activities in sequences. AB^C becomes ABC. It is a defect with Bezerra's algorithm
			#that it generates models with empty activities in sequence, which can simply be removed.
			temp = self._model[0]
			i = 1
			while i < len(self._model):
				#if pattern is not A^ or ^A, append current char to output model
				if not (self._model[i] == "^" and self._model[i-1] in self._activities):
					temp += self._model[i]
				i += 1
			self._model = temp
			
			#given above algorithm, an activity sequence may still start with '^', so remove those too
			temp = ""
			i = 0
			while i < len(self._model) - 1:
				#append current char if pattern is not ^A
				if not (self._model[i] == "^" and self._model[i+1] in self._remainingActivities):
					temp += self._model[i]
				i+=1
			temp += self._model[i]
			self._model = temp
		
	"""
	Directly implements Algorithm 4 from "Algorithms for anomaly detection from traces..." by Bezerra.
	
	An important modification, just for the sake of documenting my change, is that Bezerra'a paper calls 
	_randSplit(n-1) in multiple spots. I changed this in the locations noted below to _randSplit(n). The reason
	for the change is that _createModel() can be called (and is often) with a parameter of 2. Therefore, _randSplit(n-1)
	is _randSplit(1), which is invalid, since _randSplit() must return two positive numbers, and cannot do so for 1.
	Likewise, _randSplit() cannot return something like (0,1), since this gives rise to invalid empty loops and other bad structures.
	I just thought it was important to note the change, and document it clearly.
	
	@preventLoop: Whether or not this call of _createModel should be allowed to create a loop. Preventing loops for this recursive call
	is just a structural constraint imposed at certain points, such as preventing OR branches from starting with a loop.
	"""
	def _createModel(self, n, preventLoop=False):
		#print("n="+str(n)+" preventLoop="+str(preventLoop))
		#print("model: "+self._model)
	
		if n <= 0:
			model =  ""
		elif n == 1:
			model = self._generateRandomActivity()
		else:
			r = random.randint(1,100)
			#taken with prob 0.6: sequential workflows
			if r <= 60:
				n1,n2 = self._rndSplit(n) #in Bezerra's algorithm, this is n-1; which is problematic if n == 2, since _rndSplit cannot return two positive ints if its param is < 2.
				s = self._seq(n1, n2, preventLoop)
				model = s #elf._seq(n1, n2)

			#taken with prob 0.4: add a substructure such as AND, OR, or LOOP
			else:
				r = random.randint(1,100)
				#taken with prob 0.4 insert a single Activity
				if r >= 61:
					model = self._generateRandomActivity() + self._createModel(n-1)
					
				#taken with prob 0.3 insert OR-join
				elif r >= 31 and r <= 60:
					r = random.randint(1,100)
					#taken with prob 0.3: an OR-join with an empty branch
					if r >= 71:
						model = self._or(n-1,0)
					else:
						#taken with prob 0.7
						n1,n2 = self._rndSplit(n)  #left arg was n-1 in Bezerra's (see header comment)
						model = self._or(n1, n2)

				#Taken with prob 0.2 insert a LOOP, which shall always be prepended with an activity so we don't end up with loops configured to the end of multiple outputs: ((A|B)|(C|D))[ABC].
				#They can, however, occur multiply just before an AND/OR, such as AB[C](F|G), resulting in > 2 output edges on B
				elif r >= 11 and r <= 30 and not preventLoop:
					r = random.randint(1,100)
					#taken with prob 0.3
					if r >= 71:
						model = self._generateRandomActivity()+self._loop(n-1, 0)
					else:
						#taken with prob 0.7
						n1,n2 = self._rndSplit(n)  #n was n-1 in Bezerra's (see header comment)
						model = self._generateRandomActivity()+self._loop(n1, n2)
					
				#taken with prob 0.1 insert AND-join
				else:
					n1,n2 = self._rndSplit(n) #n was n-1 in Bezerra's (see header comment)
					model = self._and(n1, n2)
				
		return model

def usage():
	print("python ./ModelGenerator -n=(some +integer <= 60) -a=(number of anomalies to include) -config=configPath [-file=(path to output file)] [-graph=graphml save location] [-quiet dont show graph]")
	print("Optional: --loopUntilKAnomalies    If passed, models will be generated until one with k (-a) anomalies is generated, using a parameter search over pAnom.")
	
def main():
	if len(sys.argv) < 4:
		print("ERROR insufficient number of parameters")
		usage()
		exit()
	if "-n=" not in sys.argv[1]:
		print("ERROR no n parameter passed")
		usage()
		exit()
	if "-a=" not in sys.argv[2]:
		print("ERROR no num-anomalies param passed")
		usage()
		exit()
	if "-config=" not in sys.argv[3]:
		print("ERROR no config path parameter passed")
		for arg in sys.argv:
			print(arg)
		usage()
		exit()

	loopUntilKAnomalies = "--loopUntilKAnomalies" in sys.argv

	configPath = sys.argv[3].split("=")[1].strip()
	
	a = int(sys.argv[2].split("=")[1])

	#get n, the approximate number of activities to generate
	n = int(sys.argv[1].split("=")[1])
	#verify no more than 62 activities are specified; this constraint only exists because I'm using single-char, alphanumeric activity id's.
	#In the future, any arbitrary number of activities could be used, I would just need to delimit/parse the activity names.
	if n > 60: # 60 < all upper and lowercase alphanumeric chars minus some expected number of AND's, which used two activities
		print("ERROR too many activities specified. No more than 60 allowed.")
		usage()
		exit()

	ofile = None
	if len(sys.argv) > 4 and "-file=" in sys.argv[4]:
		ofile = open(sys.argv[4].split("=")[1], "w+")

	graphPath = None
	for arg in sys.argv:
		if "-graph=" in arg:
			graphPath = arg.split("=")[1]

	showPlot = "-quiet" not in sys.argv

	generator = ModelGenerator(configPath)
	generator.CreateModel(n, a, graphPath, showPlot, loopUntilKAnomalies)
	generator.PrintModel()

	if ofile != None:
		ofile.write(generator.GetModel())
		ofile.close()

if __name__ == "__main__":
	main()
