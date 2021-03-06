"""
Given a log in the .log format, this script adds noise/variance to the log according to a few parameters.

Questions linger over how to contrive noise, and its effect on results. Here's just a few notes:
	-should anomalous activities be included in the set of activities from which noise will be drawn?
	-should selection of activities as noise be performed under uniform dist, or according to activity frequency for instance?

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
	set expressed in the log at each transition. This adds 'noise' under a criterion of uniform random transitions (insertions), making
	the graph more real world like, supposedly. This is amenable to creating edge distributions with greater variance, thus allowing
	better KL metrics with respect to the regular structural patterns in the data; without this noise, the KL div is usually zero. But
	it isn't clear how much such variance is required to create global edge distributions with more variance, at the expense of poorer dendrograms.
	
	NOTE: Currently the anomalous activities, if any, are excluded from the noise selection. Should this be the case or not???
	"""
	def AddNoise1(self, logPath, outPath="noisedLog.log", noiseRate=0.1):
		activities = self._getLogActivities(logPath)
		anomalousActivities = self._getAnomalousActivities(logPath)
		#print("REGULAR ACTIVITIES: "+str(sorted(activities)))
		#print("ANOMALOUS ACTIVITIES: "+str(sorted(anomalousActivities)))
		activities = activities.difference(anomalousActivities)
		#print("SELECTED ACTIVITIES, AFTER ANOMALY REMOVAL: "+str(sorted(activities)))
		print("Generating type 1 noise, noise rate "+str(noiseRate))
		
		activities = list(activities)
		
		log = open(logPath,"r")
		traces = [line.strip() for line in log.readlines()]
		log.close()
		
		#CRITICAL: do this AFTER reading the input log, in the event that input==output log!
		outputLog = open(outPath, "w+")
		
		for trace in traces:
			#print("TRACE: "+trace+str(trace.split(",")))
			tokens = trace.split(",")
			traceNo = tokens[0]
			isAnomalous = tokens[1]
			partialOrdering = tokens[2]
			
			if len(partialOrdering) > 2: #this check is required by the defect described next line
				#CONSTRAINT ADDED: This allows noise only after the first activity, and prior to the end activity, thus preserving the endpoints
				#This is actually a defect wrt to the mined pnml model description, for which there is no a priori way to determine the beginning
				#acitivity/ies without this upstream constraint on the noise generation, such that the generated logs always have only one
				#activity with no inlinks (begin) and one with no outlinks (end). This condition is required by Pnml2Graphml; the upstream requirement for this
				#condition is the real bug/defect.
				end = partialOrdering[-1]
				begin = partialOrdering[0]
				#Note zero index is correct; the loop structure below always adds @begin before adding noise
				partialOrdering = partialOrdering[0:-1]
				
				newOrdering = []
				for activity in partialOrdering:
					newOrdering.append(activity)
					
					#inject a random post activity with probability @noiseRate
					if random.uniform(0,1) < noiseRate:
						#require: randActivity cannot be @end or @begin
						randActivity = end
						while randActivity in {end,begin}:
							randActivity = activities[random.randint(0, len(activities)-1)]
						newOrdering.append(randActivity)
						
				newOrdering = "".join(newOrdering)+end
				
			else:
				newOrdering = partialOrdering

			newTrace = ",".join([traceNo,isAnomalous,newOrdering])
			outputLog.write(newTrace+"\n")
		
		outputLog.close()

	"""
	Utility for reading a log and returning all the unique activities within it, as a list.
	This is kept simple on purpose. The anomalies and their handling is done separate since it may vary;
	but note that this will return an activity set that will include any anomalous activities not part of normal behavior.
	"""
	def _getLogActivities(self, logPath):
		log = open(logPath,"r")
		traces = [trace.strip() for trace in log.readlines()]
		log.close()
		
		#get the complete activity set expressed by the log, as a list
		availableActivities = set()
		for trace in traces:
			cols = trace.split(",")		
			partialOrdering = cols[2]
			for activity in partialOrdering:
				availableActivities.add(activity)

		#availableActivities = list(availableActivities)
		
		return availableActivities
		
	"""
	Given a log, extracts the anomalous activities from the anomalous ('+') traces in the log.
	This is defined as the set of activitie in the anomalous traces minus the non-anomalous activities.
	
	Returns: A set of anomalous activities as defined, which may be empty.
	"""
	def _getAnomalousActivities(self, logPath):
		anomalousActivities = set()
		nonAnomalousActivities = set()
		
		with open(logPath,"r") as log:
			traces = [trace.strip() for trace in log.readlines()]

		#get the complete activity sets in anomalous and non-anomalous traces expressed by the log, as a list
		for trace in traces:
			cols = trace.split(",")
			partialOrdering = cols[2]
			isAnomalous = cols[1].strip() == "+"
			for activity in partialOrdering:
				if isAnomalous:
					anomalousActivities.add(activity)
				else:
					nonAnomalousActivities.add(activity)

		return anomalousActivities.difference(nonAnomalousActivities)

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
	
	for arg in sys.argv:
		if "-inputLog=" in arg:
			inputLog = arg.split("=")[1]
		if "-outputLog=" in arg:
			outputLog = arg.split("=")[1]
		if "-noiseRate=" in arg:
			noiseRate = float(arg.split("=")[1])	
	
	noiser = LogNoiser()
	noiser.AddNoise1(inputLog, outputLog, noiseRate)

if __name__ == "__main__":
	main()
