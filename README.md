- clone from github
- touch smslog.csv
- plug in modems noting their assigned ports
- edit the config section of modemtester.py
- python ./modemtester.py

**The columns in the csv file are, in order:**

1. Origin network
2. Destination network
3. Overall message counter
4.
5. Per network message counters (I haven't found these useful and will probably remove them)
6.
7. Date and time sent
8.
9. Date and Time received (i.e. the time the message was read from the modem)
10. Seconds between datetime sent and datetime received
11. Signal strength of sending modem at time of sending
12. Signal strength of receiving modem at time of receiving
