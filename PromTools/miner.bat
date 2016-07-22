@echo calling miner.bat with %1 and %2
@echo (make sure the above path is correct, and likewise the ProM version)
call java -da -Xmx1G -XX:MaxPermSize=256m -classpath ProM66.jar -Djava.util.Arrays.useLegacyMergeSort=true org.processmining.contexts.cli.CLI %1 %2
@echo miner script ended