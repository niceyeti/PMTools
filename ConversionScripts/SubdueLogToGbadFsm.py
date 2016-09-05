"""
The gbad-fsm version of gbad requires undirected edge declaration in the .g input format.
This script just performs a find-replace of all 'd ' edge declarations with 'u '.
"""
from __future__ import print_function
import sys

def usage():
	print("python SubdueLogToGbadFsm.py [input subdue .g file] [output for fsm-formatted .g file]")

if len(sys.argv) != 3:
	print("ERROR insufficient args to SubdueLogToGbadFsm.py")
	usage()
	exit()
	
inputFile = sys.argv[1]
outputFile = sys.argv[2]
print("Converting subdue .g file "+inputFile+" to .g format at "+outputFile)
ifile = open(inputFile, "r")
ofile = open(outputFile,"w+")

log = ifile.read()
log = log.replace("\nd ","\nu ")
ofile.write(log)

ifile.close()
ofile.close()

