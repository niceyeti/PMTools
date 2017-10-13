from __future__ import print_function
import sys
import lxml.etree as etree

"""
DO NOT USE THIS SCRIPT. All the 'pretty' functions for all libraries either simply dont work,
or dont work on windows. Lxml, minidom, bs4--none of them has provided a working prettify 
function. Its beyond stupid, but thats how it is.

Just open the mxl in notepad++ and replace '>' with '>\n'.
"""



if len(sys.argv) < 2:
	print("ERROR incorect number of args to prettyXml; no prettify")
	exit()

ipath = ""
opath = ""
for arg in sys.argv:
	if "--ifile=" in arg:
		ipath = arg.split("=")[1]
	if "--ofile=" in arg:
		opath = arg.split("=")[1]
	
if ipath == "" or opath == "":
	print("ERROR incorrect params to prettyXml. Need --ifile and --ofile. Exiting with no prettify")
	exit()

x = etree.parse(ipath)
s = etree.tostring(x, pretty_print=True)

with ofile as open(opath, "w+"):
	ofile.write(s)
