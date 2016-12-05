def _getOutNeighbors(g, node):
	return [e.target for e in g.es[g.incident(node,mode="OUT")]]

def _countPaths(g, startName, endName, k):
	#mark all the nodes per number of times traversed (max of k)
	g.vs["pathCountHits"] = 0
	#get start
	startNode = g.vs.find(name=startName)
	#get immediate out-edge neighbors of START
	q = _getOutNeighbors(g, startNode)
	pathct = 0

	print("out neighbors: "+str(q))
	while len(q) > 0:
		#pop front node
		node = g.vs[q[0]]
		q = q[1:]
		print(str(node["pathCountHits"]))
		node["pathCountHits"] += 1
		if node["name"] == endName:
			print("++")
			pathct += 1
		elif node["pathCountHits"] < k:
			q += _getOutNeighbors(g, node)

	return pathct
	