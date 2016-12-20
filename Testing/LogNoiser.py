"""
Given a log in the .log format, this script adds noise/variance to the log according to a few parameters.

"""
from __future__ import print_function
import math
import random


class LogNoiser(object):
	def __init__(self):
		
	"""
	Currently just targets a single activity to replace with up to k different activity names or the target activity itself.
	This should have the effect of creating a split at the target.
	"""
	def AddNoise(logPath,outPath="noisedLog.log"):
		log = open(logPath,"r")
		noisedLog = open(outPath,"w+")
		traces = log.readlines()
		#the number of activities with which some activity will be substituted, including itself, creating a SPLIT
		ksplits = 3
		
		#determine the set of used symbols
		availableActivities = set([for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"])
		usedActivities = set()
		for trace in traces:
			partialOrdering = trace.split(",")[-1]
			for activity in partialOrdering:
				if activity not in usedActivities:
					usedActivities.add(activity)
		availableActivities = availableActivities - usedActivities

		if len(availableActivities) == 0:
			print("ERROR availableActivities empty in LogNoiser, cannot noise log "+logPath+". Exiting.")
			exit()
		if len(availableActivities) < 5:
			print("WARNING: remaining activities < 5 : "+str(availableActivities))
	
		#select a random activity in the log to randomly replace with three or so different new activity names
		target = list(usedActivities)[random.randint(0,len(usedActivities)-1)]
		#build the set of possible replacement activities, including the target itself. this may generate deduplicates
		noisyActivities = [target] + [availableActivities[random.randint(0,len(availableActivities)-1)] for i in range(0,ksplits-1)]
		noisedTraces = []
		for trace in traces:
			if target in trace: #add noise to the trace
				newTrace = trace.replace(target, noisyActivities[random.randint(0,len(noisyActivities)-1)])
			else:
				newTrace = trace
			noisedLog.write(newTrace+"\n")

		noisedLog.close()
		log.close()

def usage():
	print("usage: python LogNoiser.py")
	
def main():
	if len(sys.argv) < 3:
		print("ERROR incorrect num args: "+str(len(sys.argv)))
		usage()
		exit()

	logPath = sys.argv[1]
	outPath = sys.argv[2]
	noiser = LogNoiser()
	noiser.AddNoise(logPath,outPath)

if __name__ == "__main__":
	main()
