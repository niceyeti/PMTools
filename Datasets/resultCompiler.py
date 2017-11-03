"""
Single purpose script for iterating over the experimental results and analyzing/plotting the results.
"""
from mpl_toolkits.mplot3d import axes3d
import matplotlib.pyplot as plt
import os
import sys
import numpy as np


#Reads a single result file and returns a dict of ("metric":value) pairs
def _readResultFile(resultPath):
	result = dict()
	targets = ["precision:","recall:", "accuracy:", "error:", "fMeasure:"]
	fpCt = 0
	tnCt = 0
	
	with open(resultPath, "r") as resultFile:
		for line in resultFile:
			if any(target in line for target in targets):
				param = line.split(":")[0]
				value = float(line.split(":")[1])
				result[param] = value
			#derives fpr from other reported values in the file
			if "falsepositives:" in line.lower():
				fpCt = float(line.split(":")[1])
			if "truenegatives:" in line.lower():
				tnCt = float(line.split(":")[1])
				
	if fpCt > 0 or tnCt > 0:
		result["fpr"] = fpCt / (fpCt + tnCt)
	else:
		#this shouldn't ever happen, since it requires the outcome that all predictions be true-positives and/or false-negatives
		print("WARN fpCt and tnCt == 0 in _readResultFile for result: "+resultPath)
		result["fpr"] = 0.0

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

"""
It is useful to examine the variance of a metric, for a particular bayesThreshold and fixed theta_trace.
Hence, fix theta_trace, and plot the 2d slice at that value, with variance bars at each bayesThreshold point,
over all 60 models.
"""
def plot2DVariance(statDict, metric):
	#plot variance for highest and least theta trace value
	
	highestTheta = sorted(statDict.keys())[-1]
	lowestTheta = sorted(statDict.keys())[0]
	
	ysHighMu = [statDict[highestTheta][key][metric+"_mu"] for key in sorted(statDict[highestTheta].keys())]
	ysLowMu = [statDict[lowestTheta][key][metric+"_mu"] for key in sorted(statDict[lowestTheta].keys())]
	ysHighVar = [statDict[highestTheta][key][metric+"_var"] for key in sorted(statDict[highestTheta].keys())]
	ysLowVar = [statDict[lowestTheta][key][metric+"_var"] for key in sorted(statDict[lowestTheta].keys())]
	xs = [i for i in range(len(ysHighMu))]
	xlabels = ["0."+key.split("_")[1].replace(".txt","") for key in sorted(statDict[highestTheta].keys())]
	#plt.plot(xs, ysHigh, color="r")
	#plt.plot(xs, ysLow, color="b")
	plt.errorbar(xs, ysHighMu, yerr=ysHighVar, color="r")
	plt.errorbar(xs, ysLowMu, yerr=ysLowVar, color="b")
	plt.xticks(xs, xlabels)
	plt.title(metric[0].upper()+metric[1:]+" Variance")
	plt.legend(["theta_trace 0."+highestTheta.split("_")[-1], "theta_trace 0."+lowestTheta.split("_")[-1]], loc="best")
	plt.show()

"""
Evaluates the TPR and FPR at each value of bayes_threshold in the @result dict keys.

"""
def plotROCCurve(results):
	
	print("WARNING plotROCCurve may modify @results dict; leaving this warning as a reminder")
	#get TPR and FPR for every value of bayes threshold in @results dict inner keys over all theta values
	rocDict = dict()
	
	bayesThresholdResults = dict() #dict containing all results lists for all theta values and all 60 models
	for theta in sorted(results.keys()):
		for bayesThreshold in sorted(results[theta].keys()):
			if bayesThreshold not in rocDict.keys():
				rocDict[bayesThreshold] = []
			
			#append Results
			rocDict[bayesThreshold] += results[theta][bayesThreshold]

	xs = []	#fpr averages
	ys = []	#tpr averages
	for key in sorted(rocDict.keys()):
		threshResults = rocDict[key] #get Results for this threshold level
		print("Result count: "+str(len(threshResults)))
		avgFpr = sum([result["fpr"] for result in threshResults]) / float(len(threshResults))
		xs.append(avgFpr)
		avgTpr = sum([result["recall"] for result in threshResults]) / float(len(threshResults))
		ys.append(avgTpr)
	
	plt.plot(xs, ys, marker = 'o')
	plt.show()
	
	
"""
The results dict has outer keys thetaTraces and inner keys bayesThreshold, and values are the 60 or so Result objects for that
fixed thetaTrace and bayesThreshold value. This calculates the variance of these values at each fixed point, which is simply
the variance over all 60 results (and for each metric). These are stored in a new dictionary with the same outer key structure
as @results, but with keys for each metric: accuracy_var, recall_var, etc.
"""
def CalculateResultBayesStatDict(results):
	metrics = ["recall", "precision", "accuracy", "fMeasure"]
	statDict = dict()
	
	for thetaTrace in sorted(results.keys()):
		statDict[thetaTrace] = dict()
		for bayesThreshold in sorted(results[thetaTrace].keys()):
			statDict[thetaTrace][bayesThreshold] = dict()
			ptResults = results[thetaTrace][bayesThreshold]
			for metric in metrics:
				mean = sum([result[metric] for result in ptResults]) / float(len(ptResults))
				variance = sum([float(result[metric] - mean)**2 for result in ptResults]) / float(len(ptResults))
				statDict[thetaTrace][bayesThreshold][metric+"_var"] = variance
				statDict[thetaTrace][bayesThreshold][metric+"_mu"] = mean
				
	return statDict
	
results = IterateBayesianResults()
statDict = CalculateResultBayesStatDict(results)
#
#plot3dMetric(results, "accuracy")
#plot3dMetric(results, "recall")
#plot3dMetric(results, "precision")
#plot3dMetric(results, "fMeasure")
plot2DVariance(statDict, "accuracy")
plot2DVariance(statDict, "precision")
plot2DVariance(statDict, "recall")
plot2DVariance(statDict, "fMeasure")

plotROCCurve(results)

					
					
					










