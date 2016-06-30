import sys
import math
import random
import igraph

"""
Randomly generates process models according to Algorithm 4, in Bezerra's paper on process-mining anomaly detection.
Using that algorithm, this script randomly generates process models which can subsequently be used to generates
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
		self._anomalousOrBranchProb = 0.0
		self._anomalousLoopProb=0.0
		self._anomalyCount = 0
		self._requiredAnomalies = 999
		self._parseConfig(configPath)

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
	
		config = open(configPath,"r")
		for line in config.readlines():
			if "anomalousLoopProb=" in line:
				self._anomalousLoopProb = float(line.split("=")[1])
			if "anomalousOrBranchProb=" in line:
				self._anomalousOrBranchProb = float(line.split("=")[1])
			if "abnormalOrProbRange=" in line:
				vals = line.split("=")[1].split(",")
				self._abnormalOrProbRange = (float(vals[0]),float(vals[1]))
			if "normalOrProbRange=" in line:
				vals = line.split("=")[1].split(",")
				self._normalOrProbRange = (float(vals[0]),float(vals[1]))
			if "abnormalLoopProbRange=" in line:
				vals = line.split("=")[1].split(",")
				self._abnormalLoopProbRange = (float(vals[0]),float(vals[1]))
			if "normalLoopProbRange=" in line:
				vals = line.split("=")[1].split(",")
				self._normalLoopProbRange = (float(vals[0]),float(vals[1]))
			if "numAnomalies=" in line:
				self._requiredAnomalies = int(line.split("=")[1])
				
		if self._requiredAnomalies < 0:
			print("ERROR config did not contain numAnomalies")
		if self._abnormalOrProbRange[0] < 0.0:
			print("ERROR config did not contain abnormalOrProbRange")
		if self._normalOrProbRange[0] < 0.0:
			print("ERROR config did not contain normalOrProbRange")
		if self._abnormalLoopProbRange[0] < 0.0:
			print("ERROR config did not contain abnormalLoopProbRange")
		if self._normalLoopProbRange[0] < 0.0:
			print("ERROR config did not contain normalLoopProbRange")
		
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
		#generate a random probability number in range 0.2 to 0.8
		return self._getRandomProb(self._normalOrProbRange[0], self._normalOrProbRange[1] )

	"""
	Inverse of previous. Returns a randomly-chosen non-zero probability bounded to some very low, outlier range, such as 0.0-0.1.
	"""
	def _getAbnormalOrProb(self):
		return self._getRandomProb( self._abnormalOrProbRange[0], self._abnormalOrProbRange[1] )
		
	"""
	Returns the probability of traversing some sub-loop, under normal (non-anomalous) behavioral conditions for the model. 
	"""
	def _getNormalLoopProb(self):
		return self._getRandomProb( self._normalLoopProbRange[0], self._normalLoopProbRange[1] )
		
	def _getAbnormalLoopProb(self):
		return self._getRandomProb( self._abnormalLoopProbRange[0], self._abnormalLoopProbRange[1] )

	"""
	Builds and returns a probability expression string, given a probability and whether or not this is an anomalous event.
	
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
		#declare an anomalous branch with prob 0.30
		if (float(random.randint(1,100)) / 100.0) <= self._anomalousOrBranchProb and self._anomalyCount < self._requiredAnomalies:
			self._anomalyCount += 1
			#flip a coin to choose the anomalous branch
			if random.randint(1,2) % 2 == 0:
				isLeftBranchAnomalous=True
			else:
				isRightBranchAnomalous = True

		if not (isLeftBranchAnomalous or isRightBranchAnomalous):
			p = self._getNormalOrProb()
		else:
			p = self._getAbnormalOrProb()
		
		leftProbExpr = self._buildProbExpr(p,isLeftBranchAnomalous)
		rightProbExpr = self._buildProbExpr(1.0-p,isRightBranchAnomalous)
		probExpr = ":<"+leftProbExpr+","+rightProbExpr+">"
		
		if n2 > 0:
			#note only the left branch is prepended with an activity; this is done to guarantee at least one branch has a concrete activity, preventing branches both of which are empty
			orExpr = "("+self._generateRandomActivity()+self._createModel(n1-1)+"|" + self._createModel(n2,True)+")"+probExpr
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
	
		if isAnomalousLoop:
			p = self._getAbnormalLoopProb()
		else:
			p = self._getNormalLoopProb()
		probExpr = ":<"+self._buildProbExpr(p,isAnomalousLoop)+">"
		
		#Note the shoe-horned activity in the LOOP construct, to force there to be at least one activity in a loop
		return "["+self._generateRandomActivity()+self._seq(n1,n2,True)+"]"+probExpr #preventLoop=True prevents invalid double loops: [[AB]GHFJ]
	####### End of the grammar rules

	"""
	Resets the object state such that we're redy to create a fresh model
	"""
	def _reset(self):
		self._model = ""
		self._remainingActivities = self._activities.strip() #python pseudo deep copy
		self._anomalyCount = 0
	
	"""
	Just the outer driver for the recursive calls. Note that models are generated until one meets the num-anomalies requirement.
	An alternative is to generate models with LOOP and OR constructs, and then to flip their anomaly status to True, but the lazy way
	here is just clearer and easier, despite being less efficient.
	"""
	def CreateModel(self,n,a):
		if a > 3:
			print("WARNING generating "+str(a)+" anomalies, or more than about 3, may take too long for generator to terminate")

		#while invalid models are generated, or models without enough anomalies, create and test a new one
		isValidModel = False
		while self._anomalyCount != a or not isValidModel:
			self._reset()
			self._model = self._createModel(n,preventLoop=True) #On the first call preventLoop is set, since the outermost expr as a loop make no sense
			print('Before post-processing, model is: \n'+self._model)
			self._postProcessing() # a bandaid
			isValidModel = self._isValidModel()

		return self._model

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

		print(str(ct)+" total activities, "+str(self._anomalyCount)+" anomalies")

	"""
	For post-validation, checks that the model string is valid: not empty, doesn't contain null clauses and
	other bad structures.
	"""
	def _isValidModel(self):
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
		
		#check for consecutive empty transitions: ^^, but treat these as a warning
		if self._model.find("^^") >= 0:
			print("ERROR model string contains consecutive empty branches: "+self._model)
			
		return True

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
	def _createModel(self,n,preventLoop=False):
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

				#Taken with prob 0.2 insert a LOOP, which shall always be prepended with an acitvity so we don't end up with loops configured to the end of multiple outputs: ((A|B)|(C|D))[ABC].
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
	print("python ./ModelGenerator -n=(some +integer <= 60) -a=(number of anomalies to include) -config=configPath [-file=(path to output file)]")

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

	generator = ModelGenerator(configPath)
	generator.CreateModel(n,a)
	generator.PrintModel()

	if ofile != None:
		ofile.write(generator.GetModel())
		ofile.close()

if __name__ == "__main__":
	main()
