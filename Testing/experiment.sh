#!/bin/sh

for i in {1..60}; do
	resultDir=../Experiment/Model$i
	mkdir $resultDir
	sh recursiveSubdue.sh --generate --recurse=20 --deleteSubs --resultDest=$resultDir
done
