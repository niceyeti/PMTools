"""
Given a log in the .log format, this script adds noise/variance to the log according to a few parameters.

"""
from __future__ import print_function
import math
import random
import sys

class LogNoiser(object):
	def __init__(self):
		pass
		
	"""
	This version of adding noise proceeds through the symbol sequence of a trace in the log, 
	and with probability @noiseRate, adds a randomly selected activity from the complete activity
	set expressed in the log. This adds 'noise' under a criterion of completely random transitions, making
	the graph more real world like, supposedly.
	"""
	def AddNoise1(self, logPath, outPath="noisedLog.log", noiseRate=0.1):
		activities = self._getLogActivities(logPath)
		
		print("Generating type 1 noise, noise rate "+str(noiseRate))
		
		log = open(logPath,"r")
		traces = log.readlines()
		log.close()
		
		#CRITICAL: do this AFTER reading the input log, in the event that input==output log!
		outputLog = open(outPath, "w+")
		
		#get the complete activity set expressed by the log, as a list
		availableActivities = set()
		for trace in traces:		
			traceNo = trace.split(",")[0]
			isAnomalous = traceNo = trace.split(",")[1]
			partialOrdering = trace.split(",")[2]
			
			newOrdering = []
			for activity in partialOrdering:
				newOrdering.append(activity)
				
				#inject a random post activity with probability @noiseRate
				if random.uniform(0,1) < noiseRate:
					randActivity = activities[random.randint(0,len(activities)-1)]
					newOrdering.append(randActivity)

			newTrace = ",".join([traceNo,isAnomalous,newOrdering])
			outputLog.write(newTrace+"\n")
		
		outputLog.close()

	"""
	Utility for reading a log and returning all the unique activities within it, as a list.
	"""
	def _getLogActivities(self, logPath):
		log = open(logPath,"r")
		traces = log.readlines()
		log.close()
		
		#get the complete activity set expressed by the log, as a list
		availableActivities = set()
		for trace in traces:
			partialOrdering = trace.split(",")[2]
			for activity in partialOrdering:
				if activity not in availableActivities:
					availableActivities.add(activity)
		availableActivities = list(availableActivities)
		
		return availableActivities
		
		
	"""
	Currently just targets a single activity to replace with up to k different activities or the target activity itself.
	This has the effect of creating a split in the process model, whereby the target (and its in/out-edges) has
	a bunch of activities around it, which may be executed instead of the target, with a uniform distribution.
	"""
	def AddNoise2(self, logPath, outPath="noisedLog.log"):
		log = open(logPath,"r")
		traces = log.readlines()
		#the number of activities with which some activity will be substituted, including itself, creating a SPLIT
		ksplits = 5
		
		#determine the set of used symbols
		availableActivities = set([c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"])
		usedActivities = set()
		for trace in traces:
			partialOrdering = trace.strip().split(",")[-1]
			for activity in partialOrdering:
				if activity not in usedActivities:
					usedActivities.add(activity)
		availableActivities = list(availableActivities - usedActivities)
		usedActivities = list(usedActivities)

		if len(availableActivities) == 0:
			print("ERROR availableActivities empty in LogNoiser, cannot noise log "+logPath+". Exiting.")
			exit()
		if len(availableActivities) < 5:
			print("WARNING: remaining activities < 5 : "+str(availableActivities))
	
		noisedLog = open(outPath,"w+")
		#select a random activity in the log to randomly replace with three or so different new activity names
		target = usedActivities[random.randint(0,len(usedActivities)-1)]
		#build the set of possible replacement activities, including the target itself. this may generate deduplicates
		noisyActivities = [target] + [availableActivities[random.randint(0,len(availableActivities)-1)] for i in range(0,ksplits-1)]
		print("Noising log, replacing target >"+target+"< with any of:  "+str(noisyActivities))
		noisedTraces = []
		for trace in traces:
			tokens = trace.split(",")
			partialOrdering = tokens[-1]
			if target in partialOrdering: #add noise to the trace
				newTrace = tokens[0]+","+tokens[1]+","+partialOrdering.replace(target, noisyActivities[random.randint(0,len(noisyActivities)-1)])
			else:
				newTrace = trace
			noisedLog.write(newTrace)

		noisedLog.close()
		log.close()
		

def usage():
	print("usage: python LogNoiser.py -inputLog=[.log path] -outputLog=[output .log path] -noiseRate=[0-1.0]")
	
def main():
	if len(sys.argv) < 4:
		print("ERROR incorrect num args: "+str(len(sys.argv)))
		usage()
		exit()

	inputLog = None
	outputLog = None
	noiseRate = 0.0
	
	for arg in sys.argv
		if "-inputLog=" in arg:
			inputLog = arg.split("=")[1]
		if "-outputLog=" in arg:
			outputLog = arg.split("=")[1]
		if "-noiseRate=" in arg:
			noiseRate = float(arg.split("=")[1])	
	
	noiser = LogNoiser()
	noiser.AddNoise1(logPath,outPath,noiseRate)

if __name__ == "__main__":
	main()
