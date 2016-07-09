A collection of tools, scripts and info about the ProM plugins and tools.

ProM has a cli plugin, allowing many actions to be scripted, thereby avoiding dealing with the raw Java plugins.
See https://dirksmetric.wordpress.com/2015/03/11/tutorial-automating-process-mining-with-proms-command-line-interface/

Example usage: 
	invocation: java -da -Xmx1G -XX:MaxPermSize=256m -classpath ProM641.jar -Djava.util.Arrays.useLegacyMergeSort=true org.processmining.contexts.cli.CLI
	script:
		System.out.println("Loading log");
		log = open_xes_log_file("myLog.xes");

		System.out.println("Mining model");
		net_and_marking = alpha_miner(log);
		net = net_and_marking[0];
		marking = net_and_marking[1];

		System.out.println("Saving net");
		File net_file = new File("mined_net.pnml");
		pnml_export_petri_net_(net, net_file);

		System.out.println("done.");

	Call:
		ProM_CLI.bat -f script_alpha_miner.txt