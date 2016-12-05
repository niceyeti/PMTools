def _getOutNeighbors(g, node):
	return [e.target for e in g.es[g.incident(node,mode="OUT")]]

def _countPaths(g, startName, endName, k):
	#mark all the nodes per number of times traversed (max of k)
	g.vs["pathCountHits"] = 0
	#get start node
	startNode = g.vs.find(name=startName)
	#get immediate out-edge neighbors of START
	q = _getOutNeighbors(g, startNode)
	pathct = 0

	print("out neighbors: "+str(q))
	while len(q) > 0:
		#pop front node
		nodeId = q[0]
		node = g.vs[nodeId]
		q = q[1:]
		#get type of edge pointing to this node; note this detects if any edge pointing to node is LOOP type--unnecessary in our topology (loops only have one entrant edge), but robust
		isLoop = [e for e in g.es if e.target == nodeId][0]["type"] == "LOOP"
		print("isloop: "+str(isLoop))
		
		print(str(node["pathCountHits"]))
		node["pathCountHits"] += 1
		if node["name"] == endName:
			print("++")
			pathct += 1
		#append non-loop successors, or loop successors whom we have traversed fewer than k time, to horizon
		elif not isLoop or node["pathCountHits"] < k:
			q += _getOutNeighbors(g, node)

	return pathct
	