#This just generates a bunch of models, sleeping a small time between models, to allow me to
#visually verify the model strings.

for i in `seq 1 20`;
do
	python ModelGenerator.py -n=20 -a=1 -config=generator.config -file=testModel.txt	
	#convert the generated model to transferrable graphml
	python ModelConverter.py testModel.txt testModel.graphml --show
done



