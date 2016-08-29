/*
The template miner script. This isn't actual javascript, just the java-style script language
that is parsed by the Prom66 cli. Note the $1, $2, $3 anchors; this file is read, the anchors
are swapped with some parameters, and a new script can thereby be generated on the
fly from this template.

See these https://svn.win.tue.nl/trac/prom/browser/Packages/InductiveMiner/Trunk/src/org/processmining/plugins/InductiveMiner/mining/MiningParameters.java?rev=22217
https://svn.win.tue.nl/trac/prom/browser/Packages/InductiveMiner/Trunk/src/org/processmining/plugins/InductiveMiner/mining/MiningParametersIMi.java?rev=22217
*/

System.out.println("Loading log from $1");
log = open_xes_log_file("$1");

System.out.println("Creating settings");
org.processmining.plugins.InductiveMiner.mining.MiningParametersIMi parameters = new org.processmining.plugins.InductiveMiner.mining.MiningParametersIMi();
//org.deckfour.xes.classification.XEventClassifier classifier = new org.deckfour.xes.classification.XEventAttributeClassifier("Classifier name", "$2");

//Set noise threshold to 0.0. This is CRITICAL to make the InductiveMiner include all traces in its model.
parameters.setNoiseThreshold(0);

System.out.println("Calling miner");
pn_and_marking = mine_petri_net_with_inductive_miner_with_parameters(log, parameters);

System.out.println("Saving net");
File net_file = new File("$3");
pnml_export_petri_net_(pn_and_marking[0], net_file);

System.out.println("inductive miner done.");
System.exit(0);
