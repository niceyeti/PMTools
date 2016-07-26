"""
This just wraps the script call to the ProM cli, allowing different parameters to be passed
and generating the java-script file on the fly. The output java-script will be written to the hard-coded
file corresponding with the miner.

A typical call to the ProM cli looks like 'java -jar prom.jar -f some_file.js' where some_file.js 
contains pre-defined Java code that is parsed and executed on the fly by the Prom cli script executor. However,
this requires that some_file.js is pre-defined. Instead, I put parameters in these files by planting
anchors '$1' and them replacing them with the passed parameters. A parameterized template script file
containing such anchors is read, the anchors replaced with the passed parameters, and then the string
is written to a temp file that is then passed to the cli.

Usage: 
"""
from __future__ import print_function
import sys

def usage():
	print("Usage: python miningWrapper.py -miner=[alpha,inductive,heuristic] -ifile=process.xes -ofile=petrinet.pnml -classifierString=\"concept:name\"")


if len(sys.argv) != 5:
	print("ERROR incorrect num arguments passed to miningWrapper")
	usage()
	exit()

miner = sys.argv[1].split("=")[1].strip()
ifile = sys.argv[2].split("=")[1].strip()
ofile = sys.argv[3].split("=")[1].strip()
classifierString = sys.argv[4].split("=")[1].strip()

if miner not in ["alpha","inductive","heuristic"]:
	print("ERROR miner not found: "+miner)
	usage()
	exit()

print("Generating miner script with miner="+miner+" ifile="+ifile+" ofile="+ofile+" classifier="+classifierString)
	
if miner == "alpha":
	templatePath = "./alphaTemplate.js"
	outputPath = "./alphaMiner.js"
elif miner == "heuristic":
	templatePath = "./heuristicTemplate.js"
	outputPath = "./heuristicMiner.js"
elif miner == "inductive":
	templatePath = "./inductiveTemplate.js"
	outputPath = "./inductiveMiner.js"

templateFile = open(templatePath,"r")
templateString = templateFile.read()
	
#this is the crux of this script: swap the passed parameters for the anchors in the template
outString = templateString.replace("$1",ifile).replace("$2",classifierString).replace("$3",ofile)
outputFile = open(outputPath,"w+")
outputFile.write(outString+"\n")
outputFile.close()
