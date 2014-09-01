import sys, threading, time, signal, subprocess, re, time, queue

interval = 3 # wait for 10 seconds
window = 3 # analysis window for 120 seconds
tick = 0.1;

# TODO
def log(c):
	print(c)

''' 
Console is responsible for 
1. talking with 'user' to get 'threshold', 'logpath'
2. starting the 'monitor' in another thread with the 'threshold', 'logpath', console
3. periodically (10 secs) pull_most_hit from 'monitor' and display 
4. passively listen to 'threshold' crossing event with alert method
5. during shutdown, stop the 'monitor'
'''
class Console(object):

	def alert(self, message):
		log(message)

	def signal_handler(self, signal, frame):
		log('user interrupted, shutdown gracefully:')
		self.monitor.stop()
		sys.exit(0)

	def main(self):
		
		# add user interrupt handler
		signal.signal(signal.SIGINT, self.signal_handler)
		signal.signal(signal.SIGTERM, self.signal_handler)

		print('This is a simple log monitoring tool')

		# threshold = input('please provide high traffic alert on/off "threshold": ')
		# logpath = input('please provide "logpath": ')
		threshold = 3
		logpath = '/private/var/log/apache2/access_log'

		# TODO validation of the above

		print('high traffic threshold {0} on logpath {1} "most hit/other stats" display per {2} seconds'
			.format(threshold, logpath, interval)
		)

		self.monitor = MonitorProvider.get(threshold, logpath, self)
		self.monitor.start_thread()

		while True:
		  	time.sleep(interval)
		  	section, count = self.monitor.pull_most_hit()
		  	log('max hit is {0} on {1}'.format(count, section))

''' 
Monitor is responsible for
1. based on 'threshold', 'logpath'; start monitoring
2. maintain window stats by staring 'TimeBoundQueue' with a clear tick in another thread
3. response to pull_most_hit request
4. release file handler stuff
'''
class Monitor(threading.Thread):

	def __init__(self, *args, **kwargs):
		threading.Thread.__init__(self, *args)
		self.daemon = True
		self.threshold = kwargs['threshold']
		self.logpath = kwargs['logpath']
		self.console = kwargs['console']
		self.counter = dict()
		self.maxcount = 0
		self.maxsection = 0

	def start_thread(self):
		# start internal stats components
		self.timed_queue = TimeBoundQueueProvider.get(self.threshold, window, tick, self.console)
		self.timed_queue.start()
		# start itself
		self.start()

	def run(self):
		self.subprocess = subprocess.Popen(["tail", "-f", self.logpath], stdout=subprocess.PIPE)
		log('start tail -f process')
		while True:
			row = self.subprocess.stdout.readline().decode("utf-8")

			# TODO refactoring using visitor pattern
			section = Monitor.get_section(row)
			self.timed_queue.put(section)
			if section is not None:
				if section in self.counter:
					self.counter[section] = self.counter[section] + 1
				else:
					self.counter[section] = 1
				if self.counter[section] > self.maxcount:
					self.maxcount = self.counter[section]
					self.maxsection = section
			if not row:
				break

	def get_section(row):
		tokens = map(''.join, re.findall(r'\"GET /(.*?) HTTP.*\"', row))
		for token in tokens:
			index = token.find("/")
			if index != -1:
				return token[0:index]
			else:
				return token

	def pull_most_hit(self):
		return self.maxsection, self.counter[self.maxsection]

	def stop(self):
		log('stop tailing the log file')
		self.subprocess.kill()
		self.timed_queue.stop()

''' 
TimeBoundQueue
1. trigger alert method
2. based on tick cleaning the queue

modified based on 
http://www.acodemics.co.uk/2013/08/29/time-bound-python-queue/
'''
class TimeBoundQueue(queue.Queue, threading.Thread):

	def __init__(self, *args, **kwargs):
		threading.Thread.__init__(self, *args)
		self.daemon = True
		queue.Queue.__init__(self)
		self.threshold = kwargs['threshold']
		self.timeout = kwargs['max_time_seconds']
		self.tick = kwargs['tick']
		self.console = kwargs['console']
		self.alertflag = False

	def put(self, item):
		elem = (time.time(), item)
		self.queue.append(elem)

	# TODO hope this process is fast enough ...
	def run(self):
		while True:
			time.sleep(self.tick)
			current_time = time.time()
			valid_timestamp = current_time - self.timeout
			completed = False
			while not completed:
				try:
					timestamp, item = self.queue[0]
					if timestamp < valid_timestamp:
						# Quicker to pop than to remove a value at random position.
						self.queue.popleft()
					else:
						completed = True
				except IndexError as e:
					# No elements left
					break
			traffic_size = self.qsize()
			if traffic_size > self.threshold and not(self.alertflag):
				self.console.alert('High traffic generated an alert - hits = {0}, triggered at {1}'.format(traffic_size, current_time))
				self.alertflag = True
			if traffic_size <= self.threshold and self.alertflag:
				self.console.alert('Traffic alert off - hits = {0}, triggered at {1}'.format(traffic_size, current_time))
				self.alertflag = False

	def stop(self):
		self.queue.clear()

''' 
syntax sugar
'''
class TimeBoundQueueProvider(object):

	def get(_threshold, _max_time_seconds, _tick, _console):
		return TimeBoundQueue(
			threshold = _threshold,
			max_time_seconds = _max_time_seconds,
			tick = _tick,
			console = _console,
		)

class MonitorProvider(object):

	def get(_threshold, _logpath, _console):
		return Monitor(
			threshold = _threshold,
			logpath = _logpath,
			console = _console,
		)

if __name__ == "__main__":
	Console().main()
