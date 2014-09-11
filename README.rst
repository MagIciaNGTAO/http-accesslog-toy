======
http-accesslog-toy
======

A simple http access log monitor.

Installation
============

Install with ``pip``. ::

    pip install tailer

update manually with 

- `Tailer src <https://github.com/six8/pytailer/blob/master/src/tailer/__init__.py>`_

track this issue to see whether manual process could be ignored

- `Tailer issue <https://github.com/six8/pytailer/issues/5>`_

Usage
========

Run program with threshold 100 (traffic alert) and log path /private/var/log/apache2/access_log. ::

    python3 log_monitor.py 100 /private/var/log/apache2/access_log

Running Tests
=============

Run tests. ::

    python3 test_log_monitor.py
