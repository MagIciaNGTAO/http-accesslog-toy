usage = """\
HTTP log monitoring console program
	arg1 - an integer, specify threshold for high traffict alert on/off
	arg2 - a string, specify log file absolute path
Usage:
	python3 log_monitor.py 100 /private/var/log/apache2/access_log # start monitoring process
"""
import sys, threading, time, signal, subprocess, re, time, queue

threshold = 10
window = 120 # analysis window for 120 seconds
interval = 10 # wait for 10 seconds
tick = 0.1 # tick for 100 miliseconds

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
		log('user interrupted, shutdown gracefully!')
		self.monitor.stop()
		sys.exit(0)

	def main(self):
		
		# add user interrupt handler
		signal.signal(signal.SIGINT, self.signal_handler)
		signal.signal(signal.SIGTERM, self.signal_handler)

		try:
			global threshold #, window, interval, tick
			threshold = int(sys.argv[1])
			logpath = sys.argv[2]
			# window = int(sys.argv[3])
			# interval = int(sys.argv[4])
			# tick = float(sys.argv[5])
		except:
			log(usage)
			sys.exit(-1)

		log('high traffic threshold {0} on logpath {1} "most hit/other stats" display per {2} seconds'
			.format(threshold, logpath, interval)
		)

		self.monitor = MonitorProvider.get(threshold, logpath, self)
		self.monitor.start_thread()

		while True:
		  	time.sleep(interval)
		  	section, count = self.monitor.pull_most_hit()
		  	log('Stats for Most Hit: {0} is accessed {1} times'.format(section, count))

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
			if section is not None and section != '':
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

	# there is a fixed delay introduced by the 'tick' idea	
	# NOTE case: high traffic alert on could be more accurate if time_clean_up is called in put
	def put(self, item):
		elem = (time.time(), item)
		self.queue.append(elem)

	def run(self):
		while True:
			time.sleep(self.tick)
			clean_time = self.timed_clean_up()
			self.alert_routine(clean_time)

	def timed_clean_up(self):
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
		return current_time

	def alert_routine(self, clean_time):
		traffic_size = self.qsize()
		if traffic_size > self.threshold and not(self.alertflag):
			self.console.alert('High traffic generated an alert - hits = {0}, triggered at {1}'.format(traffic_size, clean_time))
			self.alertflag = True
		if traffic_size <= self.threshold and self.alertflag:
			self.console.alert('Traffic alert off - hits = {0}, triggered at {1}'.format(traffic_size, clean_time))
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
