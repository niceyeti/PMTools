"""
Single purpose script for iterating over the experimental results and analyzing/plotting the results.
"""
from mpl_toolkits.mplot3d import axes3d
import matplotlib.pyplot as plt
import os
import sys
import numpy as np


def _readResultFile(resultPath):
	result = dict()
	targets = ["precision:","recall:", "accuracy:", "error:", "fMeasure:"]
	
	with open(resultPath, "r") as resultFile:
		for line in resultFile:
			if any(target in line for target in targets):
				param = line.split(":")[0]
				value = float(line.split(":")[1])
				result[param] = value
				
	return result

"""
Utility for getting the x, y, z values, averaged over all models, for a particular metric, such as "fMeasure".
The z values are averaged over the list of Result objects for a particular x/y index.
"""
def _getMetricMeans(resultDict, metric):
	xdim = len(resultDict.keys())
	print(">>>: "+list(resultDict)[0])
	ydim = len(list(resultDict.items())[0][1].keys())
	xyz = np.zeros(shape=(xdim, ydim), dtype=np.float32)
	print("xyz dim: "+str(xyz.shape))
	
	row = 0
	for theta in resultDict.keys():
		col = 0
		for bayesThreshold in resultDict[theta].keys():
			vals = [result[metric] for result in resultDict[theta][bayesThreshold]]
			mean = float(sum(vals)) / float(len(vals))
			xyz[row,col] = mean
			col += 1
		row += 1
			
	return xyz
	
"""
Plots a particular metric, such as "accuracy" or "fMeasure", over all models.
"""
def plot3dMetric(resultDict, metric):
	fig = plt.figure()
	ax = fig.add_subplot(111, projection="3d")
	
	xyz = _getMetricMeans(resultDict, metric)
	xs = [i for i in range(len(resultDict.keys()))]
	ys = [i for i in range(len(list(resultDict.items())[0][1].keys()))]
	#xs = [float(key.split("_")[1]) / 10.0 for key in resultDict.keys()]
	#ys = [float(key.split("_")[1].replace(".txt","")) / 100.0 for key in list(resultDict.items())[0][1].keys()]	
	#xs = [x for x in range(xyz.shape[0])]
	#ys = [y for y in range(xyz.shape[1])]
	X, Y = np.meshgrid(xs, ys)
	
	Z = np.zeros(shape=(X.shape[0], Y.shape[1]))
	print("X shape: "+str(X.shape)+" xs len: "+str(len(xs))+"\n"+str(X))
	print("Y shape: "+str(Y.shape)+" ys len: "+str(len(ys))+"\n"+str(Y))
	print("xyz shape: "+str(xyz.shape))
	print("Z shape: "+str(Z.shape))
	
	#for row in range(xyz.shape[0]):
	#	for col in range(xyz.shape[1]):
	#		Z[row,col] = xyz[row,col]
	
	ax.plot_surface(X, Y, xyz.T, rstride=1, cstride=1)
	
	print(str(xyz))
	plt.show()
	
"""
Hard-coded iteration of the data, and results therein.

	T*
		---->	theta_*
					------>	bayes_05.txt
								bayes_10.txt
								...
								
For each test instance, there is a bayesianResult.txt file containing values for precision, recall, accuracy, etc, just for that test case.
The unique keys for test cases are the theta_trace value and the bayesThreshold value. Hence to support statistical queries along these
values, this returns a double dictionary of lists: first key = theta value, second key=bayesThreshold, value = list of Result objects at that
theta+bayesThreshold key. A "Result" object is nothing more than a dictionary of key-value pairs like "recall":0.23... as defined in each
bayesResult.txt file.
"""
def IterateBayesianResults(rootDir="Test"):
	results = dict()
	
	#iterate all the models
	for modelNumber in range(1,60):
		modelDir = rootDir + os.sep + "T"+str(modelNumber)
		#iterate the theta_trace values for this model
		for fname in os.listdir(modelDir):
			if "theta_" in fname:
				thetaDir = modelDir + os.sep + fname
				if fname not in results.keys():
					results[fname] = dict()

				#iterate the bayes
				for resultFname in os.listdir(thetaDir):
					if "bayesResult" in resultFname:
						if resultFname not in results[fname].keys():
							results[fname][resultFname] = []
					
						resultPath = thetaDir+os.sep+resultFname
						print(resultPath)
						result = _readResultFile(resultPath)
						results[fname][resultFname].append(result)

	return results

results = IterateBayesianResults()

plot3dMetric(results, "accuracy")




					
					
					










