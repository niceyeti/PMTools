"""
Some of the real world test data has enormous redundany, and many thousands of traces (~13k).
This has proven slow for SUBDUE. This script builds a histogram of all traces, then shrinks the log
so as to preserve the distribution of traces.

This is a single-purpose, hardcoded script.

"""

from __future__ import print_function
import matplotlib.pyplot as plt
import sys

"""
@traceHist: A sorted list of (traceStr,frequency) pairs, sorted descending
"""
def PlotHistogram(sortedHist):	
	#plot the histogram
	xs = [i for i in range(len(sortedHist))]
	ys = [item[1] for item in sortedHist]
	plt.xlabel("Unique Traces")
	plt.title("Trace Distribution Histogram")
	plt.ylabel("Frequency")
	plt.bar(xs, ys, width=0.2)
	plt.show()
	plt.savefig("TraceFrequencyHistogram.png")

def SimplifyLog(inPath, outPath):
	traceHist = {}
	inFile = open(inPath,"r")
	lines = [line.strip() for line in inFile.readlines() if len(line.strip()) > 5]
	inFile.close()

	print("Building trace histogram from "+str(len(lines))+" traces")
	
	#build the trace frequency dictionary
	for trace in lines:
		seq = trace.split(",")[2]
		if seq not in traceHist.keys():
			traceHist[seq] = 1
		else:
			traceHist[seq] += 1
	
	sortedHist = [item for item in traceHist.items()]
	sortedHist.sort(key = lambda item : item[1], reverse=True)
	
	#plot full histogram
	#PlotHistogram(sortedHist)
	
	#filter low-frequency traces
	freqThreshold = 4
	sortedHist = [item for item in sortedHist if item[1] > freqThreshold]
	PlotHistogram(sortedHist)
	
	#output the filtered traces
	outputFile = open(outPath,"w+")
	ctr = 1
	for trace in sortedHist:
		for i in range(1,trace[1]+1):
			outputFile.write(str(ctr)+",-,"+trace[0]+"\n")
			ctr += 1
	outputFile.close()
	
	
	

def usage():
	print("Usage: python ./SimplifyLog.py --in=[input log] --out=[output log]")

if len(sys.argv) != 3:
	print("ERROR incorrect num parameters to SimplifyLog.py.")
	usage()
	exit()
	
inPath = sys.argv[1].split("=")[1]
outPath = sys.argv[2].split("=")[1]

SimplifyLog(inPath, outPath)

