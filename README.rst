======
http-accesslog-toy
======

A simple http access log monitor.

Installation
============

Install with ``pip``.

::

    pip install tailer

update manually with 

- `Tailer src <https://github.com/six8/pytailer/blob/master/src/tailer/__init__.py>`_

Usage
========

arg1 - an integer, specify threshold for high traffict alert on/off
arg2 - a string, specify log file absolute path

python3 log_monitor.py 100 /private/var/log/apache2/access_log # start monitoring process

Running Tests
=============

Run tests ::

    python test_log_monitor.py
