#!/bin/sh

for i in {1..60}; do
	mkdir Experiment/Model$i
	sh recursiveSubdue.sh --generate --recurse=10 --deleteSubs --resultDest=../Experiment
done

