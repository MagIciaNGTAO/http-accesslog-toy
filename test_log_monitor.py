'''
1. start test by invoking Console().main()
2. appending to ./access.log file by copying from ./sample.log
3. assert based on appending speed and configuration
'''
import os, sys, itertools, time
from unittest.mock import MagicMock
from log_monitor import *

log_file_name = './access.log'
sample_file_name = './sample.log'
threshold = 500
waiting_time = 3
access_frequency = 0.005
window = 5 # small time window of traffic alert for testing

def clean():
    # remove
    try:
        os.remove(log_file_name)
    except OSError:
        pass        

clean()

# create
log_file = open(log_file_name, 'a')
    
# start monitor
sut = Console()
sut.start_routine(threshold, log_file_name, window)
sut.fixture = MagicMock()

with open(sample_file_name) as f:
    for line in f:
        log_file.write(line)
        time.sleep(access_frequency)
        log_file.flush() 

# assert alert on is called
sut.fixture.assert_any_call('on')

time.sleep(waiting_time)

# assert alert off is called
sut.fixture.assert_any_call('off')

sut.stop()

clean()