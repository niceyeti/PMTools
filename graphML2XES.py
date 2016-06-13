
from future import print_function
import sys
import xes

def usage():
	print("Usage: python ./g2xes.py [path to .g input file] [path to output file] [optional process name]")
	print("Example: python ./g2xes.py process.g process.xes ")
	
def main():
	if len(sys.argv) < 3:
		usage()
		return 0
	try:
		open(sys.argv[1],"r").close()
		outputFile = open(sys.argv[2],"w+")
		g = igraph.Graph.Read(sys.argv[1])
		outputFile.write("%Vertices")
		for v in g.vs:
			line = str(v.index)+" "+v["name"]+"\r\n"
			outputFile.write(line)
		outputFile.write("%Edges")		
		for e in g.es:
			line = str(e.source)+" "+str(e.target)+" "+e["name"]+"\r\n"
			outputFile.write(line)
		print("Conversion completed and written to: "+sys.argv[2])
		outputFile.close()
	except IOError:
		print("Input file not found: "+sys.argv[1])
		return 0
