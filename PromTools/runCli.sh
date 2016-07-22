#!/bin/bash
echo calling runCli.sh with $1 and $2
echo (make sure the above path is correct, and likewise the ProM version)
java -da -Xmx1G -XX:MaxPermSize=256m -classpath ProM66.jar -Djava.util.Arrays.useLegacyMergeSort=true org.processmining.contexts.cli.CLI $1 $2
echo ProM mining script complete.
