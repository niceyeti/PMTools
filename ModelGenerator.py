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
	def __init__(self):
		#activity dictionary; let activities be defined by simple symbols in Sigma, each with some label
		#self.activities = {'A':"PullLever",'B':"PushButton",'C':"SpinWheel",'D':"TwistKnob",'E':"PullSpring",'F':"TootWhistle",'G':"RingBell",'H':"TapGauge",'I':"WipeForehead",'J':"ReadGauge",'K':"SmellSmoke",'L':"TapKeys",'M':"PushPedal"}
		self.symbols = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
		self.model = ""
		
	"""
	Returns a random activity from the activity set.
	"""
	def _randomActivity(self):
		randomIndex = random.randint(0,len(self.symbols)-1)
		return self.symbols[randomIndex]

	"""
	Implements the rndSplit() function, directly from Bezerra. Generates two numbers in Z+,
	such that n1 + n2 = n
	"""
	def _rndSplit(self,n):
		if n <= 1:
			print("WARNING: ERROR, n <= 1 in _rndSplit(). n must be >= 2, s.t. n1, n2 can both be positive.")
			return 0,1
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
		return self._getRandomProb(0.2, 0.8)

	"""
	Inverse of previous. Returns a randomly-chosen non-zero probability bounded to some very low, outlier range, such as 0.0-0.1.
	"""
	def _getAbnormalOrProb(self):
		return self._getRandomProb(0.0, 0.1)
		
	"""
	Returns the probability of traversing some sub-loop, under normal (non-anomalous) behavioral conditions for the model. 
	"""
	def _getNormalLoopProb(self):
		return self._getRandomProb(0.2,0.8)
		
	def _getAbnormalLoopProb(self):
		return self._getRandomProb(0.001,0.1)

	"""
	Builds and returns a probability expression string, given a probability and whether or not this is an anomalous event.
	
	Given: 0.2, True, returns "0.2/True"
	"""
	def _buildProbExpr(self,p,isAnomalous):
		return str(p)+"/"+str(isAnomalous)	
		
	###### The grammar rules. Note the ones that are always prepended with a non-empty activity, as a requirement.
	"""
	AND is the simplest, creating two branches, both of which shall be taken so there are no associated probs, and neither branch may be empty.
	"""
	def _and(self,n1,n2):
		return "("+self._randomActivity()+self._createModel(n1-1)+"&"+self._randomActivity()+self._createModel(n2-1)+")"
		
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
	def _or(self,n1,n2,isLeftBranchAnomalous=False,isRightBranchAnomalous=False):
		p = self._getNormalOrProb()
		leftProbExpr = self._buildProbExpr(p,isLeftBranchAnomalous)
		rightProbExpr = self._buildProbExpr(1.0-p,isRightBranchAnomalous)
		probExpr = ":<"+leftProbExpr+","+rightProbExpr+">"
		
		if n2 > 0:
			#note only the left branch is prepended with an activity; this is done to guarantee at least one branch has a concrete activity, preventing branches both of which are empty
			orExpr = "("+self._randomActivity()+self._createModel(n1-1)+"|" + self._createModel(n2,True)+")"+probExpr
		else:
			#note only the left branch is prepended with an activity; this is done to guarantee at least one branch has a concrete activity, preventing branches both of which are empty
			orExpr = "("+self._randomActivity()+self._createModel(n1-1)+"|^)"+probExpr
			
		return orExpr
		
	def _loop(self,n1,n2,isAnomalousLoop=False):
		if isAnomalousLoop:
			p = self._getAbnormalLoopProb()
		else:
			p = self._getNormalLoopProb()
		probExpr = ":<"+self._buildProbExpr(p,isAnomalousLoop)+">"
		
		return "["+self._seq(n1,n2,True)+"]"+probExpr #preventLoop=True prevents invalid double loops: [[AB]GHFJ]
	####### End of the grammar rules

	"""
	Just the outer driver for the recursive calls
	"""
	def CreateModel(self,n):
		self.model = self._createModel(n,preventLoop=True) #On the first call preventLoop is set, since the outermost expr as a loop make no sense
		self._postProcessing() # a bandaid
		return self.model

	def PrintModel(self):
		print("Model:\n"+self.model)
		i = 0
		l = []
		for c in self.model:
			if c in self.symbols:
				l += c
				i += 1
		print(str(i)+" total activities, "+str(len(set(l)))+" unique activities")

	"""
	Cleans up model string after construction. Any potential errors should be fixed
	in the construction definition, not here. This is simply a bandaid for filtering and
	transforming the model.
	"""
	def _postProcessing(self):
		#Replace ^^ (consecutive empty activities) with nil
		self.model = self.model.replace("^^","")
	
		#Remove empty activities in sequences. AB^C becomes ABC. It is a defect with Bezerra's algorithm
		#that it generates models with empty activities in sequence, which can simply be removed.
		temp = self.model[0]
		i = 1
		while i < len(self.model):
			#if pattern is not A^ or ^A, append current char to output model
			if not (self.model[i] == "^" and self.model[i-1] in self.symbols):
				temp += self.model[i]
			i += 1
		self.model = temp
		
		#given above algorithm, an activity sequence may still start with '^', so remove those too
		temp = ""
		i = 0
		while i < len(self.model) - 1:
			#append current char if pattern is not ^A
			if not (self.model[i] == "^" and self.model[i+1] in self.symbols):
				temp += self.model[i]
			i+=1
		temp += self.model[i]
		self.model = temp
		
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
		#print("model: "+self.model)
	
		if n <= 0:
			#print("EMPTY TRANSITION")
			model =  ""
		elif n == 1:
			model = self._randomActivity()
		else:
			r = random.randint(1,100)
			#taken with prob 0.6: sequential workflows
			if r <= 60:
				n1,n2 = self._rndSplit(n) #in Bezerra's algorithm, this is n-1; which is problematic if n == 2, since _rndSplit cannot return two positive ints if its param is < 2.
				s = self._seq(n1, n2, preventLoop)
				model = s #elf._seq(n1, n2)

			#taken with prob 0.4
			else:
				r = random.randint(1,100)
				#taken with prob 0.4 insert a single Activity
				if r >= 61:
					a = self._randomActivity()
					model = a + self._createModel(n-1)
					
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

				#taken with prob 0.2 insert a LOOP, which shall always be prepended with an acitvity so we don't end up with loops configured to the end of multiple outputs: ((A|B)|(C|D))[ABC]
				elif r >= 11 and r <= 30 and not preventLoop:
					r = random.randint(1,100)
					#taken with prob 0.3
					if r >= 71:
						model = self._randomActivity()+self._loop(n-1, 0)
					else:
						#taken with prob 0.7
						n1,n2 = self._rndSplit(n)  #n was n-1 in Bezerra's (see header comment)
						model = self._randomActivity()+self._loop(n1, n2)
					
				#taken with prob 0.1 insert AND-join
				else:
					n1,n2 = self._rndSplit(n) #n was n-1 in Bezerra's (see header comment)
					model = self._and(n1, n2)
				
		return model

def usage():
	print("python ./ModelGenerator -n=(some integer) [-file=(path to output file)]")

def main():
	if len(sys.argv) < 2:
		print("ERROR insufficient number of parameters")
		usage()
		exit()
	if "-n=" not in sys.argv[1]:
		print("ERROR no n parameter passed")
		exit()

	n = int(sys.argv[1].split("=")[1])

	ofile = None
	if len(sys.argv) > 2 and "-file=" in sys.argv[2]:
		ofile = open(sys.argv[2].split("=")[1], "w")
		
	generator = ModelGenerator()
	generator.CreateModel(n)
	generator.PrintModel()

	if ofile != None:
		ofile.write(generator.model)
		ofile.close()

if __name__ == "__main__":
	main()
