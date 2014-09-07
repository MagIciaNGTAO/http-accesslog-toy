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
1. get 'threshold', 'log_path' from cli
2. START:    starting the 'timed_queue' in another thread, then 'monitor' in another thread
3. POLL:     in another thread, periodically ('interval' secs) pull stats from 'monitor'
4. LISTEN:   passively listen to 'threshold' crossing event with alert method
5. STOP:     during shutdown, stop those threads in the opposite sequence (reverse-dependency)
'''
class Console(object):

    def alert(self, signal, message):
        log(message)
        # em ... testing purpose
        self.fixture(signal)

    def fixture(self, signal):
        # no-op
        pass

    def signal_handler(self, signal, frame):
        log('user interrupted, shutdown gracefully!')
        self.stop()
        sys.exit(0)

    def stop(self):
        self.polling_stop.set()
        self.monitor.stop()
        self.timed_queue.stop()

    def stats_poll(self, stop_event):
        while not stop_event.is_set():
            stop_event.wait(interval)
            section, count = self.monitor.pull()
            log('Stats for Most Hit: {0} is accessed {1} times'.format(section, count))

    def main(self):
        self.polling = True

        # add user interrupt handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            global threshold, window #, interval, tick
            threshold = int(sys.argv[1])
            log_path = sys.argv[2]
            window = int(sys.argv[3])
            # interval = int(sys.argv[4])
            # tick = float(sys.argv[5])
        except:
            log(usage)
            sys.exit(-1)

        log('high traffic threshold {0} on log_path {1} "most hit/other stats" display per {2} seconds'
            .format(threshold, log_path, interval)
        )

        self.timed_queue = TimeBoundQueueProvider.get(threshold, window, tick, self)
        self.timed_queue.start()

        self.monitor = MonitorProvider.get(threshold, log_path, self, self.timed_queue)
        self.monitor.start()

        self.polling_stop = threading.Event()
        self.stats_polling_thread = threading.Thread(target = self.stats_poll, args=(self.polling_stop,))
        self.stats_polling_thread.start()
        

''' 
Monitor is responsible for
1. based on 'threshold', 'log_path'; start monitoring
2. response to poll request from 'console'
3. release file handler stuff
'''
class Monitor(threading.Thread):

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args)
        self.daemon = True
        self.threshold = kwargs['threshold']
        self.log_path = kwargs['log_path']
        self.console = kwargs['console']
        self.timed_queue = kwargs['timed_queue']
        self.counter = dict()
        self.maxcount = 0
        self.maxsection = None

    def run(self):
        self.subprocess = subprocess.Popen(["tail", "-f", self.log_path], stdout=subprocess.PIPE)
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

    def pull(self):
        if self.maxsection is not None :
            return self.maxsection, self.counter[self.maxsection]
        return 'not exist', 0

    def stop(self):
        log('stop tailing the log file')
        self.subprocess.kill()
        # TODO self._stop.set()

''' 
TimeBoundQueue
1. trigger traffic alert
2. based on tick interval to clean up the queue

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
            self.console.alert('on', 'High traffic generated an alert - hits = {0}, triggered at {1}'.format(traffic_size, clean_time))
            self.alertflag = True
        if traffic_size <= self.threshold and self.alertflag:
            self.console.alert('off', 'Traffic alert off - hits = {0}, triggered at {1}'.format(traffic_size, clean_time))
            self.alertflag = False

    def stop(self):
        self.queue.clear()
        # self._stop.set()

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

    def get(_threshold, _log_path, _console, _timed_queue):
        return Monitor(
            threshold = _threshold,
            log_path = _log_path,
            console = _console,
            timed_queue = _timed_queue,
        )

if __name__ == "__main__":
    Console().main()
