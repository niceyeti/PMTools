#python ../ConversionScripts/convertModelActivities.py	--minedGraphml=$minedGraphmlPath --activityDictPath=activityDict.txt

#Simple script for swapping the activities in some mined process model graphml file (output by pnmlConverter) with single letter activities given by some activity dict
#Just a glue utility

from __future__ import print_function
import sys
import os
import igraph
import traceback

def main():
	minedGraphmlPath = ""
	activityDictPath = ""
	for arg in sys.argv:
		if "--minedGraphmlPath=" in arg:
			minedGraphmlPath = arg.split("=")[-1]
		if "--activityDictPath=" in arg:
			activityDictPath = arg.split("=")[-1]

	print(str(sys.argv))
	if len(minedGraphmlPath) == 0:
		print("ERROR no mined graphml path passed")
		usage()
		exit()
	if len(activityDictPath) == 0:
		print("no activity dict path passed")
		usage()
		exit()	

	graph = igraph.Graph.Read(minedGraphmlPath)
	igraph.plot(graph)

	try:
		activityDict = eval(open(activityDictPath, "r").read())
	except:
		print("ERROR There was an issue reading activity dict from "+activityDictPath)
		traceback.print_exc()
		exit()

	#validate the activities/graph
	graphKeys = [v["name"] for v in graph.vs if v["name"] not in ["START","END"]]
	if len(activityDict.keys()) != len(graphKeys):
		print("ERROR activity dict contains "+str(len(activityDict.keys()))+" activities but graph contains "+str(len(graph.vs)))
		print(str([v["name"] for v in graph.vs]))
		print(str(activityDict.keys()))
		exit()

	for key in graphKeys:
		if key not in activityDict.keys():
			print("ERROR activity "+key+" found in graph but not in activity dict")
			print("Graph activities: ")
			for vertex in graph.vs:
				print("\t"+vertex["name"])
			print("Dict activities from "+activityDictPath)
			for activity in activityDict.keys():
				print("\t"+activity)
			print(str(activityDict))
			exit()

	for v in graph.vs:
		if v["name"] not in ["START","END"]:
			v["name"] = activityDict[v["name"]]
			v["label"] = v["name"]

	graph.write(minedGraphmlPath)
	#graph.write_graphml(minedGraphmlPath.replace(".graphml","_REPLACED.graphml"))

def usage():
	print("python convertModelActivities.py --minedGraphmlPath=[] --activityDictPath=[]")


if __name__ == "__main__":
	main()