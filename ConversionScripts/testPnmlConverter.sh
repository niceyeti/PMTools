
for i in $(seq 60); do
	python Pnml2Graphml.py "..\Datasets\Test_0\T$i\anomaly_0\testModel.pnml" junk.graphml --show
done
