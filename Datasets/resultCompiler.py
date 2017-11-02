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
	for theta in sorted(resultDict.keys()):
		col = 0
		for bayesThreshold in sorted(resultDict[theta].keys()):
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
	xlabels = [str(f) for f in sorted([float(key.split("_")[1])/10.0 for key in resultDict.keys()])]
	ys = [i for i in range(len(list(resultDict.items())[0][1].keys()))]
	ylabels = [str(f) for f in sorted([float(key.split("_")[1].replace(".txt","")) / 100.0 for key in list(resultDict.items())[0][1].keys()])]
	
	#print(str(xlabels))
	#print(str(ylabels))
	#exit()
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
	ax.set_zlabel(metric[0].upper()+metric[1:])
	plt.xticks(xs, xlabels, rotation=60)
	plt.yticks(ys, ylabels, rotation=60)
	ax.set_xlabel('Theta Trace',labelpad=10)
	ax.set_ylabel('Bayes Threshold', labelpad=12)
	#print(str(xyz))
	plt.show()
	
"""
The results of this experiment are three dimensional, since we have two parameters
to vary: theta_trace and alpha_bayes. This plots a performance metric wrt only one of these
parameters, collapsing/summing the other.

For a given metric (recall, precision, accuracy), this plots that metric on
the y axis, and the wrt the xaxis (theta_trace or bayes_threshold).

@resultDict: The results dictionary, with theta trace first keys, bayes threshold second keys
@metric: "recall", "precision", "accuracy", or "fMeasure"
@xaxis: The parameter to use as an input, such that @metric is a function of this. Valid values are only "thetaTrace" and "bayesThreshold".
"""
def plot2DMetric(resultDict, metric, xaxis):
	pass
	#ys = []
	#if "trace" in xaxis.lower():
	#	
	#elif "bayes" in xaxis.lower():
	#	
	#else:
	#	print("ERROR xaxis not found in plt2DMetric:"+xaxis)
		
		
		






	
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
		modelDir = rootDir + os.sep + "T" + str(modelNumber)
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
plot3dMetric(results, "fMeasure")
plot3dMetric(results, "recall")
plot3dMetric(results, "precision")




					
					
					










