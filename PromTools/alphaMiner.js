/*
The template miner script. This isn't actual javascript, just the java-style script language
that is parsed by the Prom66 cli. Note the ../SyntheticData/testTraces.xes, Activity, ../SyntheticData/testModel.pnml anchors; this file is read, the anchors
are swapped with some parameters, and a new script can thereby be generated on the
fly from this template.
*/

System.out.println("Loading log from ../SyntheticData/testTraces.xes");
log = open_xes_log_file("../SyntheticData/testTraces.xes");

System.out.println("Got log: ");
System.out.println(log);

System.out.println("Getting log info");
org.deckfour.xes.info.XLogInfo logInfo = org.deckfour.xes.info.XLogInfoFactory.createLogInfo(log);

System.out.println("Getting classifier");
org.deckfour.xes.classification.XEventClassifier classifier = logInfo.getEventClassifiers().iterator().next();
//org.deckfour.xes.classification.XEventClassifier classifier = new org.deckfour.xes.classification.XEventAttributeClassifier("Classifier name", "concept:name", "Activity");
System.out.println("Classifier: ");
System.out.println(classifier);

System.out.println("Mining model with alpha miner");
net_and_marking = alpha_miner(log, classifier);
net = net_and_marking[0];
marking = net_and_marking[1];

System.out.println("Saving net");
File net_file = new File("../SyntheticData/testModel.pnml");
pnml_export_petri_net_(net, net_file);

System.out.println("alpha miner done.");
System.exit(0);



