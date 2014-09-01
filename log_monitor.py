import sys, threading, time, signal, subprocess

''' 
Console is responsible for 
1. talking with 'user' to get 'threshold', 'logpath'
2. starting the 'monitor' in another thread with the 'threshold', 'logpath', console
3. periodically (10 secs) pull_most_hit from 'monitor' and display 
4. passively listen to 'threshold' crossing event with alert method
5. during shutdown, stop the 'monitor'
'''
class Console(object):

	interval = 10 # wait for 10 seconds

	def alert(self, traffic_type):
		print(traffic_type)

	def signal_handler(self, signal, frame):
		print('user interrupted, shutdown gracefully:')
		self.__monitor.stop()
		sys.exit(0)

	def main(self):
		
		# add user interrupt handler
		signal.signal(signal.SIGINT, self.signal_handler)
		signal.signal(signal.SIGTERM, self.signal_handler)

		print('This is a simple log monitoring tool')

		threshold = input('please provide high traffic alert on/off "threshold": ')
		logpath = input('please provide "logpath": ')
		# TODO validation of the above

		print('high traffic threshold {0} on logpath {1} "most hit/other stats" display per {2} seconds'
			.format(threshold, logpath, Console.interval)
		)

		self.__monitor = MonitorProvider.get(threshold, logpath, self)
		self.__monitor.start()

		while True:
		  	time.sleep(Console.interval)
		  	print(self.__monitor.pull_most_hit())

''' 
MonitorProvider is just a syntax sugar to get Monitor instance 
'''
class MonitorProvider(object):

	def get(_threshold, _logpath, _console):
		return Monitor(
			threshold = _threshold,
			logpath = _logpath,
			console = _console,
		)

''' 
Monitor is responsible for
1. based on 'threshold', 'logpath'; start monitoring - it's similar to tail -f ... not yet sure how it looks like in python :( 
2. maintain stat
3. response to pull_most_hit request
4. trigger alert method
5. release file handler stuff
'''
class Monitor(threading.Thread):

	def __init__(self, *args, **kwargs):
		self.__threshold = kwargs['threshold']
		self.__logpath = kwargs['logpath']
		self.__console = kwargs['console']
		# self.__queue = Queue.Queue(maxsize=1000) # buffer at most 100 lines
		threading.Thread.__init__(self, *args)
		self.daemon = True

	def run(self):
		self.__subprocess = subprocess.Popen(["tail", "-f", self.__logpath], stdout=subprocess.PIPE)
		while True:
			line = self.__subprocess.stdout.readline()
			# self.__queue.put(line)
			print(line)
			if not line:
				break
			self.__console.alert('high traffic')

	def pull_most_hit(self):
		return 'TOPHITURL'

	def stop(self):
		# TODO
		print('kill log tailing process')
		self.__subprocess.kill()
		
# print self.__queue.get() # blocks
# print self.__queue.get_nowait() # throws Queue.Empty if there are no lines to read

if __name__ == "__main__":
	Console().main()
