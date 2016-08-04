/*
The template miner script. This isn't actual javascript, just the java-style script language
that is parsed by the Prom66 cli. Note the testTraces.xes, Activity, testModel.pnml anchors; this file is read, the anchors
are swapped with some parameters, and a new script can thereby be generated on the
fly from this template.
*/

System.out.println("Loading log");
log = open_xes_log_file("testTraces.xes");

System.out.println("Getting log info");
org.deckfour.xes.info.XLogInfo logInfo = org.deckfour.xes.info.XLogInfoFactory.createLogInfo(log);

System.out.println("Setting classifier");
//org.deckfour.xes.classification.XEventClassifier classifier = logInfo.getEventClassifiers().iterator().next();
org.deckfour.xes.classification.XEventClassifier classifier = new org.deckfour.xes.classification.XEventAttributeClassifier("Classifier name", "Activity");

System.out.println("Creating heuristics miner settings");
org.processmining.plugins.heuristicsnet.miner.heuristics.miner.settings.HeuristicsMinerSettings hms = new org.processmining.plugins.heuristicsnet.miner.heuristics.miner.settings.HeuristicsMinerSettings();
hms.setClassifier(classifier);

System.out.println("Calling miner");
net = mine_for_a_heuristics_net_using_heuristics_miner(log, hms);

System.out.println("Saving net...");
File net_file = new File("testModel.pnml");
pnml_export_petri_net_(net, net_file);

//System.out.println("Visualize");
//javax.swing.JComponent comp = visualize_heuristicsnet_with_annotations(net);
//javax.swing.JFrame frame = new javax.swing.JFrame();
//frame.add(comp);
//frame.setSize(400,400);
//frame.setVisible(true);

System.out.println("heuristic miner done.");
System.exit(0);

