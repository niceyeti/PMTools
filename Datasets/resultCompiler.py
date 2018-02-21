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

	#Left a corner case in result files: there is an edge case when all traces are negatives, and all predictions are true
	#In this case, precision and recall are 1.0, which results from reasoning their value as TP/FN/FP approach zero.
	#Also, it is vacuously true that for 100% negatives and no positive predictions, then the method found "100% of the positives", which is none.	
	#TODO: This should really be fixed in AnomalyReporter.py, the source of the result files
	if result["accuracy"] == 1.0 and result["precision"] == 0.0:
		result["precision"] = 1.0  #follows from def precision
	if result["accuracy"] == 1.0 and result["recall"] == 0.0:
		result["recall"] = 1.0	      #follows from def recall
	
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
	#print(">>>: "+list(resultDict)[0])
	ydim = len(list(resultDict.items())[0][1].keys())
	xyz = np.zeros(shape=(xdim, ydim), dtype=np.float32)
	#print("xyz dim: "+str(xyz.shape))
	
	row = 0
	for theta in sorted(resultDict.keys(), key=lambda s: float(s.split("_")[1])):
		col = 0
		for bayesThreshold in sorted(resultDict[theta].keys(), key=lambda s: float(s.replace(".txt","").split("_")[1])):
			vals = [result[metric] for result in resultDict[theta][bayesThreshold]]
			mean = float(sum(vals)) / float(len(vals))
			xyz[row,col] = mean
			col += 1
		row += 1

	return xyz

"""
Plotting labels is a nuisance when they get too dense. This utility slices and returns
the xs and labels at the sliced indices.
"""
def _sliceLabels(xs, labels):
	step = int(len(xs) / 10)
	if step > 1:
		slicedLabels = []
		slicedXs = []
		for i in range(len(labels)):
			if i % step == 0:
				slicedLabels.append(labels[i])
				slicedXs.append(xs[i])
	else:
		slicedXs = xs
		slicedLabels = labels
				
	return slicedXs, slicedLabels

"""
Plots a particular metric, such as "accuracy" or "fMeasure", over all models.
"""
def plot3dMetric(resultDict, metric, resultDir, xlabel, ylabel,xlabels=None,ylabels=None):
	fig = plt.figure()
	ax = fig.add_subplot(111, projection="3d")
	xyz = _getMetricMeans(resultDict, metric)
	#make the labels, max of 10 so they aren't crowded; these xs are not plotted, they are just for indexing the labels
	sortedKeys = sorted(resultDict.keys(), key=lambda s: float(s.split("_")[1]))
	print("SORTED KEYS: "+str(sortedKeys))
	xs = [i for i in range(len(sortedKeys))]
	if xlabels is None:
		if "anomaly" in xlabel.lower():
			xlabels = [str(f) for f in [float(key.split("_")[1])/100.0 for key in sortedKeys]]
		else:
			xlabels = [str(f) for f in [float(key.split("_")[1])/10.0 for key in sortedKeys]]
	ys = [i for i in range(len(list(resultDict.items())[0][1].keys()))]
	#ys = [i for i in range(len([(key,resultDict[key]) for key in sortedKeys])[0][1].keys()))]

	if ylabels is None:
		ylabels = [str(f) for f in sorted([float(key.split("_")[1].replace(".txt","")) / 100.0 for key in list(resultDict.items())[0][1].keys()])]
	X, Y = np.meshgrid(xs, ys)
	#Z = np.zeros(shape=(X.shape[0], Y.shape[1]))

	if len(xs) > 10:
		xs, xlabels = _sliceLabels(xs, xlabels)
	if len(ys) > 10:
		ys, ylabels = _sliceLabels(ys, ylabels)
		#step = int(len(ylabels) / 10)
		#if step > 1:
		#	slicedYLabels = []
		#	slicedYs = []
		#	for i in range(int(len(ylabels) / step)):
		#		index = i * step
		#		if index < len(ylabels):
		#			slicedYLabels.append(ylabels[index])
		#			slicedYs.append(ys[index])
		#	ylabels = slicedYLabels
		#	ys = slicedYs

	print("X shape: "+str(X.shape)+" xs len: "+str(len(xs))+"\n"+str(X))
	print("Y shape: "+str(Y.shape)+" ys len: "+str(len(ys))+"\n"+str(Y))
	print("xyz shape: "+str(xyz.shape))
	#print("Z shape: "+str(Z.shape))
	print("xlabels: "+str(xlabels)+"xs: "+str(xs))
	print("ylabels: "+str(ylabels)+"ys: "+str(ys))
	
	#force plot to 0.0 to 1.0 static z-range
	axes = plt.gca()
	axes.set_zlim([0.0,1.0])
	
	ax.plot_surface(X, Y, xyz.T, rstride=1, cstride=1)
	ax.set_zlabel(metric[0].upper()+metric[1:])
	plt.xticks(xs, xlabels, rotation=60)
	plt.yticks(ys, ylabels, rotation=60)
	title = metric[0].upper()+metric[1:].lower()
	if "fmeasure" in title.lower():
		title = title.replace("measure", "-measure")
	plt.title(title)
	ax.set_xlabel(xlabel,labelpad=12)
	ax.set_ylabel(ylabel, labelpad=12)
	#print(str(xyz))
	if resultDir[-1] != os.sep:
		resultDir += os.sep
	plt.savefig(resultDir+metric+"_3d.png")
	plt.show()
	
	with open(resultDir+metric+"_3d.txt", "w+") as of:
		varDict = dict()
		varDict["xs"] = X
		varDict["ys"] = Y
		varDict["zs"] = xyz.T
		varDict["xticks"] = {"xs":xs, "xlabels":xlabels}
		varDict["yticks"] = {"ys":ys, "ylabels":ylabels}
		varDict["xlabel"] = xlabel
		varDict["ylabel"] = ylabel
		varDict["title"] = title
		of.write(str(varDict))

"""
Hard-coded iteration of the data, and results therein.

	theta-dirname -> bayes-fname              -> [60 results in T1-T60]
	"anomaly_35" -> "bayesResults_08.txt" -> [result1, result2, ...]
	
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
def IterateBayesianResults(rootDir="Test", thetaFolderPrefix="theta_"):
	results = dict()
	
	print("Compiling bayesian results...        >>>>excluding bayesResult_07.txt<<<<  ...")
	
	#iterate all the models
	for modelNumber in range(1,31):
		modelDir = rootDir + os.sep + "T" + str(modelNumber)
		
		#iterate the theta_trace of anomaly_theta values for this model
		for fname in os.listdir(modelDir):
			if thetaFolderPrefix in fname:
				thetaDir = modelDir + os.sep + fname
				if fname not in results.keys():
					results[fname] = dict()

				#iterate the bayes parameter results
				for resultFname in os.listdir(thetaDir):
					if "bayesResult" in resultFname and resultFname.lower() != "bayesresult_07.txt":
						if resultFname not in results[fname].keys():
							results[fname][resultFname] = []
					
						resultPath = thetaDir+os.sep+resultFname
						print(resultPath)
						result = _readResultFile(resultPath)
						#left a corner case in result files: there is an edge case when all traces are negatives, and all predictions are true
						#In this case, precision and recall are 1.0, which results from reasoning their value as TP/FN/FP approach zero.
						#Also, it is vacuously true that for 100% negatives and no positive predictions, then the method found "100% of the positives", which is none.
						results[fname][resultFname].append(result)

	return results

"""
Hard-coded iteration of the data, and results therein for the experiment using models with multiple anomalies.

	A[k] -> bayes-fname              -> [30 results in T1-T30]
	"A0" -> "bayesResults_08.txt" -> [result1, result2, ...result30]
	
	A*
		---->	T*
					------>	bayes_04.txt
								bayes_06.txt
								...
								
For each test instance, there is a bayesianResult.txt file containing values for precision, recall, accuracy, etc, just for that test case.
The unique keys for test cases are the theta_trace value and the bayesThreshold value. Hence to support statistical queries along these
values, this returns a double dictionary of lists: first key = theta value, second key=bayesThreshold, value = list of Result objects at that
theta+bayesThreshold key. A "Result" object is nothing more than a dictionary of key-value pairs like "recall":0.23... as defined in each
bayesResult.txt file.
"""
def IterateMultipleAnomalyResults(rootDir="Multiple_Anomaly_Rerun"):
	results = dict()
	if rootDir[-1] != os.sep:
		rootDir=rootDir+os.sep
	
	print("Compiling bayesian results for multiple anomalous structure experiment...        >>>>excluding bayesResult_07.txt<<<<  ...")
	
	for anomModel in [0,1,2,4,8,16,32]:
		anomModelKey = "A_"+str(anomModel)
		if anomModelKey not in results.keys():
			results[anomModelKey] = dict()
	
		#iterate all the models
		for modelNumber in range(1,30):
			modelDir = rootDir + "A{}{}T{}".format(anomModel, os.sep, modelNumber)
			#iterate the bayes parameter results
			for resultFname in os.listdir(modelDir):
				if "bayesResult" in resultFname and resultFname.lower() != "bayesresult_07.txt":
					if resultFname not in results[anomModelKey].keys():
						results[anomModelKey][resultFname] = []
				
					resultPath = modelDir+os.sep+resultFname
					print(resultPath)
					result = _readResultFile(resultPath)
					results[anomModelKey][resultFname].append(result)

	return results
	
"""
Interactively slices results for a particular bayes parameter value input by the user.

This could encompass 2D plotting of performance metrics at that slice, but command line output
is fine as far as gathering results for the paper.

@results: A result dict per IterateBayesianResults, outer keys like "theta_x" and inner keys as "bayesResult_xx.txt"
"""
def sliceBayesResults(results):
	
	metrics = ["accuracy","recall", "fMeasure", "precision"]
	
	#python 2/3 hack
	try:
		my_scanf = raw_input
	except:
		my_scanf = input
		
	validInput = False
	
	while not validInput:
		paramString = my_scanf("Enter bayes parameter xx, per 'bayesResult_xx.txt' along which to slice results: ")
		validInput = len(paramString) == 2 and paramString[0] in "0123456789" and paramString[1] in "0123456789"
		if validInput:
			for metric in metrics:
				ys = [] #one y-value per outer parameter: anomaly_xx or theta_x
				
				#eg, for "anomaly_xx" in result.keys()
				for param in results.keys():
					paramDict = results[param]
					for bayesFile in paramDict.keys():
						if "bayesResult_"+paramString in bayesFile:
							paramResults = [result[metric] for result in paramDict[bayesFile]]
							param_y_bar = float(sum(paramResults)) / len(paramResults)
							ys.append(param_y_bar) #the y/performance value for this fixed point parameter value: theta_5, anomaly_35, or what have you
							
				print(metric+" ys: "+str(ys)+"   y_avg: "+str(sum(ys)/float(len(ys))))
			
			my_scanf("Enter anything to continue")
		else:
			print("Incorrect input. Retry")
	
	
	
"""
Iteration of the sampling-algorithm results, the algorithm with which my method is being compared.
The sampling algorithm places a sampleAlgoTest folder in each log directory, within which there is a 
sampleResult.txt file formatted exactly as per the bayesian result files. The algorithm took so long to run,
there was no parameter tuning of evaluation parameters, as for the bayesion method.

So this just returns a dicitonary of lists of result objects: ["theta_5"] -> [result1, result2, ...]
The dict key is the model parameter ("theta_x" or "anomaly_x"), and the list should be of the length of the
number of models successfully tested.
"""
def IterateSampleAlgorithm2dResults(rootDir="Test", thetaFolderPrefix="theta_"):
	results = dict()
	
	print("Compiling sample algorithm results...   ")
	
	#iterate all the models
	for modelNumber in range(1,30):
		modelDir = rootDir + os.sep + "T" + str(modelNumber)
		
		#iterate the theta_trace or anomaly_theta values for this model
		for fname in os.listdir(modelDir):
			if thetaFolderPrefix in fname:
				thetaDir = modelDir + os.sep + fname
				if fname not in results.keys():
					results[fname] = list()

				#There are no parameters to iterate for these results; the algorithm was run for fixed parameters once for each model
				resultPath = thetaDir+os.sep+"sampleAlgoTest/sampleResult.txt"
				if os.path.exists(resultPath):
					result = _readResultFile(resultPath)
					results[fname].append(result)
				else:
					print("ERROR no result path found for: "+resultPath)

	return results

"""
Plots a set of results with @metric on the y axis and the keys of @resultDict on the x axis. These keys refer to lists of
result objects, which are averaged for the passed @metric to derive each y value at that point.

NOTE: This is currently just written for theta_x testing, not anomaly_x, since that would require differentiation the "x" label values
more precisely than here.


@resultDict: A dictionary expected to have a single outer key and a list of result objects per each model (so sixty or so). key: "theta_5" -> [result1, result2, ...]

"""
def plot2DMetric(resultDict, metric, resultDir, xlabel, ylabel, xlabels=None):
	xs = [i for i in range(len(resultDict.keys()))]
	ys = []
	xLabels = []
	
	for outerKey in sorted(resultDict.keys()):
		xLabels.append("0."+outerKey.split("_")[-1])
		mu = sum([float(resultDict[metric]) for resultDict in resultDict[outerKey]]) / float(len(resultDict[outerKey]))
		ys.append(mu)
		
	print("ys: "+str(ys)+"  ybar: "+str(float(sum(ys)) / float(len(ys))))
	print("xs: "+str(xs))
	#force plot 0.0 to 1.0 range
	axes = plt.gca()
	#axes.set_xlim([0.0,1.0])
	axes.set_ylim([0.0,1.0])
	
	if "fmeasure" not in metric.lower():
		title = metric[0].upper()+metric[1:]
	else:
		title = "F1-Measure"
	plt.title(title)

	if xlabels is not None: #override calculated labels with passed labels
		xLabels = xlabels

	plt.xticks(xs, xLabels)
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)
	plt.plot(xs, ys)
	plt.show()
	
"""
It is useful to examine the variance of a metric, for a particular bayesThreshold and fixed theta_trace.
Hence, fix theta_trace, and plot the 2d slice at that value, with variance bars at each bayesThreshold point,
over all 60 models.
"""
def plot2DVariance(statDict, metric, resultDir):
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
	xs, xlabels = _sliceLabels(xs, xlabels)
	plt.xticks(xs, xlabels)
	title = metric[0].upper()+metric[1:]+" Variance"
	plt.title(title)
	legendList = ["theta_trace 0."+highestTheta.split("_")[-1], "theta_trace 0."+lowestTheta.split("_")[-1]]
	plt.legend(legendList, loc="best")
	if resultDir[-1] != os.sep:
		resultDir += os.sep
	plt.savefig(resultDir+metric+"_2dVariance.png")
	plt.show()

	with open(resultDir+metric+"_2dVariance.txt", "w+") as of:
		varDict = dict()
		varDict["xs"] = xs
		varDict["ysHighMu"] = ysHighMu
		varDict["ysHighVar"] = ysHighVar
		varDict["ysLowMu"] = ysLowMu
		varDict["ysLowVar"] = ysLowVar
		varDict["xlabels"] = xlabels
		varDict["title"] = title
		varDict["legendList"] = legendList
		of.write(str(varDict))

"""
Evaluates the TPR and FPR at each value of bayes_threshold in the @result dict keys.

"""
def plotROCCurve(results, resultDir):
	
	if resultDir[-1] != os.sep:
		resultDir += os.sep
	
	print("WARNING plotROCCurve may modify @results dict; leaving this warning as a reminder")
	#get TPR and FPR for every value of bayes threshold in @results dict inner keys over all theta values
	rocDict = dict()
	
	bayesThresholdResults = dict() #dict containing all results lists for all theta values and all 60 models: 
	for theta in sorted(results.keys()):
		for bayesThreshold in sorted(results[theta].keys()):
			if bayesThreshold not in rocDict.keys():
				rocDict[bayesThreshold] = []
			
			#append Results
			rocDict[bayesThreshold] += results[theta][bayesThreshold]

	# the [0.0,1.0] are to shove in the endpoints of an ROC curve, just for plotting
	xs = [0.0,1.0]	#fpr averages
	ys = [0.0,1.0]	#tpr averages
	for key in sorted(rocDict.keys()):
		threshResults = rocDict[key] #get Results for this threshold level
		#print("Result count: "+str(len(threshResults)))
		avgFpr = sum([result["fpr"] for result in threshResults]) / float(len(threshResults))
		xs.append(avgFpr)
		avgTpr = sum([result["recall"] for result in threshResults]) / float(len(threshResults))
		ys.append(avgTpr)
	
	xyTuples = [(xs[i], ys[i]) for i in range(len(xs))]
	xyTuples = sorted(xyTuples, key=lambda tup: tup[1])
	xs = [xyTuples[i][0] for i in range(len(xyTuples))]
	ys = [xyTuples[i][1] for i in range(len(xyTuples))]
	
	#force plot 0.0 to 1.0 range
	axes = plt.gca()
	axes.set_xlim([0.0,1.0])
	axes.set_ylim([0.0,1.0])
	
	plt.title("ROC Curve")
	plt.plot(xs, ys, marker = 'o')
	#the reference line
	xs = [0.0, 1.0]
	ys = [0.0, 1.0]
	plt.plot(xs, ys, '--',color='orange')
	plt.savefig(resultDir+"roc.png")
	plt.show()
	
	with open(resultDir+"roc.txt", "w+") as of:
		varDict = dict()
		varDict["xs"] = xs
		varDict["ys"] = ys
		of.write(str(varDict))
	
"""
The results dict has outer keys thetaTraces and inner keys bayesThreshold, and values are the 60 or so Result objects for that
fixed thetaTrace and bayesThreshold value. This calculates the variance and mean of these values at each fixed point, which is simply
the variance over all 60 results (and for each metric). These are stored in a new dictionary with the same outer key structure
as @results, but with keys for each metric: accuracy_var, recall_var, etc.
"""
def CalculateBayesResultStatDict(results):
	metrics = ["recall", "precision", "accuracy", "fMeasure"]
	statDict = dict()  # triple dict: theta -> threshold -> metric -> value     e.g., "anomaly_2" -> "bayesResult_08.txt" -> 
	
	for thetaTrace in sorted(results.keys()): #sorts the strings, "anomaly_35" or "theta_5", where the numbers are assumed div 100; note that this is not a good sort, as anomaly_2 and anomaly_25 will be adjacet, but the output dict are not ordered
		statDict[thetaTrace] = dict()
		for bayesThreshold in sorted(results[thetaTrace].keys()):  #sorts the bayesian fnames; bayesResults_00.txt thru bayesResults_98.txt
			statDict[thetaTrace][bayesThreshold] = dict()
			ptResults = results[thetaTrace][bayesThreshold]
			for metric in metrics:
				mean = sum([result[metric] for result in ptResults]) / float(len(ptResults))
				variance = sum([float(result[metric] - mean)**2 for result in ptResults]) / float(len(ptResults))
				statDict[thetaTrace][bayesThreshold][metric+"_var"] = variance
				statDict[thetaTrace][bayesThreshold][metric+"_mu"] = mean
				
	return statDict
"""
Similar to prior, but the @results dict for the sample-algorithm is only a dict of lists of result objects,
since the algorithm was run on only a single set of given parameters per log.


"""
def CalculateSampleAlgoResultStatDict(results):
	metrics = ["recall", "precision", "accuracy", "fMeasure"]
	statDict = dict()  # double dict: theta -> metric -> value
	
	for thetaTrace in sorted(results.keys()): #sorts the strings, "anomaly_35" or "theta_5", where the numbers are assumed div 100; note that this is not a good sort, as anomaly_2 and anomaly_25 will be adjacet, but the output dict are not ordered
		statDict[thetaTrace] = dict()

		ptResults = results[thetaTrace]
		for metric in metrics:
			mean = sum([result[metric] for result in ptResults]) / float(len(ptResults))
			variance = sum([float(result[metric] - mean)**2 for result in ptResults]) / float(len(ptResults))
			statDict[thetaTrace][metric+"_var"] = variance
			statDict[thetaTrace][metric+"_mu"] = mean

	return statDict

def usage():
	print("usage: python resultCompiler.py --rootDir=[]  --thetaFolderPrefix=[]  one of: [--normal, --multipleAnomModels, --sampleAlgo]")
	print("--normal: Iterate the original experiment results")
	print("--multipleAnomModels: iterate the experiment testing models with multiple anomalies")
	print("--sampleAlgo: Iterate the sample algorithm results")
	
if len(sys.argv) < 2:
	print("Insufficient arguments passed. Need --rootDir= and --thetaFolderPrefix=")
	print("Pass --sampleAlgo to run sample-algorithm results compilation from sampleAlgoTest/ folders within target test folders")
	usage()
	exit()

thetaFolderPrefix = "theta_"
rootDir = "Test"
sampleAlgo = False
multipleAnomModels=False
normalAlgo=False
for arg in sys.argv:
	if "--rootDir=" in arg:
		rootDir = arg.split("=")[1]
	if "--thetaFolderPrefix=" in arg:
		thetaFolderPrefix = arg.split("=")[1]
	if "--sampleAlgo" in arg:
		sampleAlgo = True
	if "--normalAlgo" in arg:
		normalAlgo = True
	if "--multipleAnomModels" in arg:
		multipleAnomModels = True
		
if (multipleAnomModels + normalAlgo + sampleAlgo) > 1:
	print("ERROR Only one of --normalAlgo, --multipleAnomModels, or --sampleAlgo may be passed!")
	usage()
	exit()

if (multipleAnomModels + normalAlgo + sampleAlgo) == 0:
	print("ERROR Only no param --normalAlgo, --multipleAnomModels, or --sampleAlgo passed!")
	usage()
	exit()

if (normalAlgo or sampleAlgo) and thetaFolderPrefix.strip() == "":
	pint("ERROR no theta folder prefix passed")
	usage()
	exit()

	
if "anomaly" in thetaFolderPrefix.lower():
	xlabel = "Theta-Anomaly"
	resultDir = rootDir+"_AnomalyTheta_Results"+os.sep
elif "theta_" in thetaFolderPrefix.lower():
	xlabel = "Theta-Trace"
	resultDir = rootDir+"_ThetaTrace_Results"+os.sep
	
if sampleAlgo:
	ylabel = "Performance"
elif normalAlgo or multipleAnomModels:
	ylabel = "Bayes Threshold"

if multipleAnomModels:
	xlabel = "Anomalous Structures"
	
if not os.path.exists(resultDir):
	os.mkdir(resultDir)

if sampleAlgo: #compile sample-algorithm results
	results = IterateSampleAlgorithm2dResults(rootDir, thetaFolderPrefix)
	statDict = CalculateSampleAlgoResultStatDict(results)

	plot2DMetric(results, "accuracy", resultDir, xlabel, ylabel)
	plot2DMetric(results, "recall", resultDir, xlabel, ylabel)
	plot2DMetric(results, "precision", resultDir, xlabel, ylabel)
	plot2DMetric(results, "fMeasure", resultDir, xlabel, ylabel)
	#plot2DVariance(statDict, "accuracy", resultDir)
	#plot2DVariance(statDict, "precision", resultDir)
	#plot2DVariance(statDict, "recall", resultDir)
	#plot2DVariance(statDict, "fMeasure", resultDir)

	#plotROCCurve(results, resultDir)
elif normalAlgo:  #run/build bayesian results
	results = IterateBayesianResults(rootDir, thetaFolderPrefix)
	statDict = CalculateBayesResultStatDict(results)

	sliceBayesResults(results)
	
	plot3dMetric(results, "accuracy", resultDir, xlabel, ylabel)
	plot3dMetric(results, "recall", resultDir, xlabel, ylabel)
	plot3dMetric(results, "precision", resultDir, xlabel, ylabel)
	plot3dMetric(results, "fMeasure", resultDir, xlabel, ylabel)
	plot2DVariance(statDict, "accuracy", resultDir)
	plot2DVariance(statDict, "precision", resultDir)
	plot2DVariance(statDict, "recall", resultDir)
	plot2DVariance(statDict, "fMeasure", resultDir)

	plotROCCurve(results, resultDir)
elif multipleAnomModels:
	results = IterateMultipleAnomalyResults(rootDir)
	statDict = CalculateBayesResultStatDict(results)

	#sliceBayesResults(results)
	xlabels = [str(i) for i in [0,1,2,4,8,16,32]]
	plot3dMetric(results, "accuracy", resultDir, xlabel, ylabel, xlabels=xlabels)
	plot3dMetric(results, "recall", resultDir, xlabel, ylabel, xlabels=xlabels)
	plot3dMetric(results, "precision", resultDir, xlabel, ylabel, xlabels=xlabels)
	plot3dMetric(results, "fMeasure", resultDir, xlabel, ylabel, xlabels=xlabels)
	#plot2DVariance(statDict, "accuracy", resultDir)
	#plot2DVariance(statDict, "precision", resultDir)
	#plot2DVariance(statDict, "recall", resultDir)
	#plot2DVariance(statDict, "fMeasure", resultDir)

	plotROCCurve(results, resultDir)
