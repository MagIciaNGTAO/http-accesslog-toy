import sys, threading, time

''' Console is responsible for 
1. talking with 'user' to get 'threshold', 'logpath'
2. starting the 'monitor' in another thread with the 'threshold', 'logpath', console
3. periodically (10 secs) pull_most_hit from 'monitor' and display 
4. passively listen to 'threshold' crossing event with alert method
5. during shutdown, stop the 'monitor' ?? lol ... daemon was sufficient in Java ...
'''
class Console(object):

	interval = 10 # wait for 10 seconds

	def alert(self, traffic_type):
		print(traffic_type)

	def main(self):
		
		print('This is a simple log monitoring tool')

		_threshold = input('please provide high traffic alert on/off "threshold": ')
		_logpath = input('please provide "logpath": ')

		print('high traffic threshold {0} on logpath {1} "most hit/other stats" display per {2} seconds'
			.format(_threshold, _logpath, Console.interval)
		)

		# TODO validation of the above

		thread = Monitor(
			threshold=_threshold,
			logpath=_logpath,
			console=self,
		)
		thread.start()

		while True:
		  	time.sleep(Console.interval)
		  	print(thread.pull_most_hit())

''' Monitor is responsible for
1. TODO based on 'threshold', 'logpath'; start monitoring - it's similar to tail -f ... not yet sure how it looks like in python :( 
2. TODO maintain stat
3. response to pull_most_hit request
4. trigger alert method
5. TODO release file handler stuff ??
'''
class Monitor(threading.Thread):

	def __init__(self, *args, **kwargs):
		self.__threshold = kwargs['threshold']
		self.__logpath = kwargs['logpath']
		self.__console = kwargs['console']
		threading.Thread.__init__(self, *args)
		self.daemon = True

	def run(self):
		while True:
			# TODO real log task
			time.sleep(5)
			self.__console.alert('high traffic')

	def pull_most_hit(self):
		return 'TOPHITURL'

if __name__ == "__main__":
	sys.exit(Console().main())
