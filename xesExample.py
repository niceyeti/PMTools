

traces = [
	[
		{"concept:name" : "Register", "org:resource" : "Bob"},
		{"concept:name" : "Negotiate", "org:resource" : "Sally"},
		{"concept:name" : "Negotiate", "org:resource" : "Sally"},
		{"concept:name" : "Sign", "org:resource" : "Dan"},
		{"concept:name" : "Sendoff", "org:resource" : "Mary"}
	],
	[
		{"concept:name" : "Register", "org:resource" : "Bob"},
		{"concept:name" : "Negotiate", "org:resource" : "Sally"},
		{"concept:name" : "Sign", "org:resource" : "Dan"},
		{"concept:name" : "Sendoff", "org:resource" : "Mary"}
	],
	[
		{"concept:name" : "Register", "org:resource" : "Bob"},
		{"concept:name" : "Negotiate", "org:resource" : "Sally"},
		{"concept:name" : "Sign", "org:resource" : "Dan"},
		{"concept:name" : "Negotiate", "org:resource" : "Sally"},
		{"concept:name" : "Sendoff", "org:resource" : "Mary"}
	],
	[
		{"concept:name" : "Register", "org:resource" : "Bob"},
		{"concept:name" : "Sign", "org:resource" : "Dan"},
		{"concept:name" : "Sendoff", "org:resource" : "Mary"}
	]
]


log = xes.Log()
for trace in traces:
	t = xes.Trace()
	for event in trace:
		e = xes.Event()
		e.attributes = [
			xes.Attribute(type="string", key="concept:name", value=event["concept:name"]),
			xes.Attribute(type="string", key="org:resource", value=event["org:resource"])
		]
		t.add_event(e)
	log.add_trace(t)
log.classifiers = [
	xes.Classifier(name="org:resource",keys="org:resource"),
	xes.Classifier(name="concept:name",keys="concept:name")
]

open("example.xes", "w").write(str(log))
