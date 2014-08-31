''' console is responsible for 
1. talking with 'user' to get 'threshold', 'logpath'
2. starting the 'monitor' in another thread with the 'threshold', 'logpath'
3. periodically (10 secs) pull the stats from 'monitor' and display 
4. passively listen to 'threshold' crossing event and inform the 'user'
5. during shutdown, stop the 'monitor'
'''

print("I am the console")


