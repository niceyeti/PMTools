from pntools import petrinet

##returns a list of petrinets parsed from a given file
#pn = petrinet.parse_pnml_file("sample.pnml")
##for  p in pn:
#	print(str(p))

import xml.dom.minidom

xml = xml.dom.minidom.parse("sample.pnml") # or xml.dom.minidom.parseString(xml_string)
pretty_xml_as_string = xml.toprettyxml()
print(pretty_xml_as_string)
open("example.pnml","w+").write(pretty_xml_as_string)