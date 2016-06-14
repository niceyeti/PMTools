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
			return 0,1
		else:
			r = random.randint(0,n)
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

	###### The grammar rules
	"""
	AND is the simplest, creating two branches, both of which shall be taken so there are no associated probs.
	"""
	def _and(self,n1,n2):
		return "("+self._createModel(n1)+"&"+self._createModel(n2)+")"
		
	def _seq(self,n1,n2):
		return self._createModel(n1)+self._createModel(n2)
		
	def _or(self,n1,n2):
		p = self._getNormalOrProb()
		return "("+self._createModel(n1)+"|" + self._createModel(n2)+"):<"+str(p)+","+str(1.0-p)+">"
		
	def _loop(self,n1,n2):
		p = self._getNormalLoopProb()
		return "["+self._seq(n1,n2)+"]:<"+str(p)+">"
	####### End of the grammar rules

	"""
	Just the outer driver for the recursive calls
	"""
	def CreateModel(self,n):
		self.model = self._createModel(n)
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
		
		#given above algorithm, an activity sequence may still start with '^', so no remove those too
		temp = ""
		i = 0
		while i < len(self.model) - 1:
			#apped current char if pattern is not ^A
			if not (self.model[i] == "^" and self.model[i+1] in self.symbols):
				temp += self.model[i]
			i+=1
		temp += self.model[i]
		self.model = temp
		
	"""
	Directly implements Algorithm 4 from "Algorithms for anomaly detection from traces..." by Bezerra.
	
	"""
	def _createModel(self,n):
		#print("n="+str(n))
		#print("model: "+self.model)
	
		if n == 0:
			return "^"  #Effectively null; note this means that any OR, AND, or LOOP may contain an empty branch or subprocess, effectively allowing jumps/skips
		elif n == 1:
			return self._randomActivity()
		else:
			r = random.randint(1,100)

			#taken with prob 0.6: sequential workflows
			if r <= 60:
				n1,n2 = self._rndSplit(n-1)
				return self._seq(n1, n2)

			#taken with prob 0.4
			r = random.randint(1,100)
			#taken with prob 0.4 insert a single Activity
			if r >= 61:
				a = self._randomActivity()
				return a+self._createModel(n-1)

			#taken with prob 0.3 insert OR
			elif r >= 31 and r <= 60:
					r = random.randint(1,100)
					#taken with prob 0.3: an OR with an empty branch
					if r >= 71:
						return self._or(n-1,0)
					#taken with prob 0.7
					n1,n2 = self._rndSplit(n-1)
					return self._or(n1, n2)

			#taken with prob 0.2 insert a LOOP
			elif r >= 11 and r <= 30:
				r = random.randint(1,100)
				#taken with prob 0.3
				if r >= 71:
					return self._loop(n-1, 0)
				#taken with prob 0.7
				n1,n2 = self._rndSplit(n-1)
				return self._loop(n1-1, n2-1)
			
			#taken with prob 0.1 insert AND
			else:
				n1,n2 = self._rndSplit(n-1)
				return self._and(n1-1, n2-1)				

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
