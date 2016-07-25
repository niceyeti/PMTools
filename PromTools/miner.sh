#!/bin/bash
promJarPath="C:\Users\jesse\ProM66\ProM66.jar"

echo calling miner.sh with $1 and $2
echo "(make sure above path is correct, likewise the ProM version; dont forget -f param before script filename)"
java -da -Xmx1G -XX:MaxPermSize=256m -classpath $promJarPath -Djava.util.Arrays.useLegacyMergeSort=true org.processmining.contexts.cli.CLI $1 $2
echo ProM mining script complete.
