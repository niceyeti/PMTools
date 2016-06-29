echo Building process model with appr 10 activities...
python ModelGenerator.py -n=10 -file=junk.txt
python ModelConverter.py junk.txt 
python DataGenerator.py 