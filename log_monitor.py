import sys, threading, time, signal, subprocess, re

''' 
Console is responsible for 
1. talking with 'user' to get 'threshold', 'logpath'
2. starting the 'monitor' in another thread with the 'threshold', 'logpath', console
3. periodically (10 secs) pull_most_hit from 'monitor' and display 
4. passively listen to 'threshold' crossing event with alert method
5. during shutdown, stop the 'monitor'
'''
class Console(object):

	interval = 3 # wait for 10 seconds

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

		# threshold = input('please provide high traffic alert on/off "threshold": ')
		# logpath = input('please provide "logpath": ')
		threshold = 100
		logpath = '/Users/mingtaozhang/http-accesslog-toy/access.log'
		# TODO validation of the above

		print('high traffic threshold {0} on logpath {1} "most hit/other stats" display per {2} seconds'
			.format(threshold, logpath, Console.interval)
		)

		self.__monitor = MonitorProvider.get(threshold, logpath, self)
		self.__monitor.start()

		while True:
		  	time.sleep(Console.interval)
		  	section, count = self.__monitor.pull_most_hit()
		  	print('max hit is {0} on {1}'.format(count, section))

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
1. based on 'threshold', 'logpath'; start monitoring
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
		self.__counter = dict()
		self.__maxcount = 0
		self.__maxsection = 0
		threading.Thread.__init__(self, *args)
		self.daemon = True

	def run(self):
		self.__subprocess = subprocess.Popen(["tail", "-f", self.__logpath], stdout=subprocess.PIPE)
		log('start tail -f process')
		while True:
			row = self.__subprocess.stdout.readline().decode("utf-8")
			section = Monitor.get_section(row)
			# TODO self.__console.alert('high traffic')
			if section != "":
				if section in self.__counter:
					self.__counter[section] = self.__counter[section] + 1
				else:
					self.__counter[section] = 1
				if self.__counter[section] > self.__maxcount:
					self.__maxcount = self.__counter[section]
					self.__maxsection = section
			if not row:
				break

	def get_section(row):
		tokens = map(''.join, re.findall(r'\"GET /(.*?) HTTP.*\"', row))
		for token in tokens:
			index = token.find("/")
			if index != -1:
				token = token[0:index]
		return token

	def pull_most_hit(self):
		return self.__maxsection, self.__counter[self.__maxsection]

	def stop(self):
		log('kill tail -f process')
		self.__subprocess.kill()

def log(c):
	print(c)

if __name__ == "__main__":
	Console().main()
