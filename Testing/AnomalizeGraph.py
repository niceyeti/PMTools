"""
Given that we have generated a model G (some ground-truth process graph), we desire
to add anomalies according to the following type:
	-insertions
	-deletions
	-modification
Insertions: information being forwarded to some new node before returning to the node from which 
the original process thread departed (hence a new loop).
Deletions: An arc that bypasses one or more nodes along an underlying process model. For example,
for a linear process A->B->C->D, we might delete C, giving A->B->D.
Modifications: Rather than bypass some node(s), we replace them. So for the linear process from before,
we might instead see A->B->Z->D.
"""



