% 3
XP
v 1 START
v 2 RegisterRequest
v 3 ExamineCasually
v 4 CheckTicket
v 5 Decide
v 6 ReinitiateRequest
v 7 ExamineThoroughly
v 8 PayCompensation
v 9 END
e 1 2 Pete
e 2 3 Pete
e 3 4 Mike
e 4 5 Ellen
e 5 6 Sara
e 6 7 Sara
e 7 4 Sean
e 4 5 Pete
e 5 8 Sara
e 8 9 Ellen

% 2
XP
v 1 START
v 2 RegisterRequest
v 3 ExamineCasually
v 4 CheckTicket
v 5 Decide
v 6 ReinitiateRequest
v 7 ExamineThoroughly
v 8 PayCompensation
v 9 END
e 1 2 Mike
e 2 4 Mike
e 4 3 Mike
e 3 5 Sean
e 5 8 Sara
e 8 9 Ellen

% 1
XP
v 1 RejectRequest
v 1 START
v 2 RegisterRequest
v 3 ExamineCasually
v 4 CheckTicket
v 5 Decide
v 6 ReinitiateRequest
v 7 ExamineThoroughly
v 8 PayCompensation
v 9 END
e 1 2 Pete
e 2 7 Pete
e 7 4 Sue
e 4 5 Mike
e 5 1 Sara
e 1 9 Pete

% 6
XP
v 1 RejectRequest
v 1 START
v 2 RegisterRequest
v 3 ExamineCasually
v 4 CheckTicket
v 5 Decide
v 6 ReinitiateRequest
v 7 ExamineThoroughly
v 8 PayCompensation
v 9 END
e 1 2 Mike
e 2 3 Mike
e 3 4 Ellen
e 4 5 Mike
e 5 8 Sara
e 8 9 Mike

% 5
XP
v 1 RejectRequest
v 1 START
v 2 RegisterRequest
v 3 ExamineCasually
v 4 CheckTicket
v 5 Decide
v 6 ReinitiateRequest
v 7 ExamineThoroughly
v 8 PayCompensation
v 9 END
e 1 2 Ellen
e 2 3 Ellen
e 3 4 Mike
e 4 5 Pete
e 5 6 Sara
e 6 4 Sara
e 4 3 Ellen
e 3 5 Mike
e 5 6 Sara
e 6 3 Sara
e 3 4 Sue
e 4 5 Pete
e 5 1 Sara
e 1 9 Mike

% 4
XP
v 1 RejectRequest
v 1 START
v 2 RegisterRequest
v 3 ExamineCasually
v 4 CheckTicket
v 5 Decide
v 6 ReinitiateRequest
v 7 ExamineThoroughly
v 8 PayCompensation
v 9 END
e 1 2 Pete
e 2 4 Pete
e 4 7 Mike
e 7 5 Sean
e 5 1 Sara
e 1 9 Ellen

