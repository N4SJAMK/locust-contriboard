# locust-contriboard
Locust tests for contriboard

To run these tests:
```
locust -f locust-tests-new.py -H http://*address*/ TeamboardUser
```


# To run thease tests with more than one machine

Make sure every machine has same version of locust and locust scripts

specify one machine to operate as master with command: 
```
locust -f locust-tests-new.py --master -H http://_targetaddresshere_/ TeamboardUser
```


In every slave machine use this command to operate as slave: 
```
locust -f locust-tests-new.py --slave --master-host=_masters ip address here_ -H http://_targetaddresshere_/ TeamboardUser
```


Now you can enter locust control panel with browser by navigating to masters ip address and port :8089




### Notice that masters are not sending requests to the target, master only uses slaves to hatch users and send requests.
