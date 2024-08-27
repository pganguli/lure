import os
from typing import Hashable, TYPE_CHECKING, List, Dict
from enum import Enum
import simpy
import re

if TYPE_CHECKING:
    from lure.config.configuration import LoggerConfig

class LogLevel(Enum):
    """Logging levels for LureLogger. In ascending importance, DEBUG, INFO, WARNING, ERROR, and CRITICAL. Each level includes the information of all the levels above it. \
        For example, anything set to INFO will contain WARNING, ERROR, and CRITICAL logs, but not DEBUG logs.
    """
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    def __ge__(self, other):
        l = ["debug", "info", "warning", "error", "critical"]
        return l.index(self.value) >= l.index(other.value)

    def __str__(self):
        return self.name

class LureLogger:
    """Logging class for Lure simulations.
    """

    def __init__(self, logger_config: 'LoggerConfig', simpy_env: simpy.core.Environment, output_dir: str):
        self.config = {}
        self.default_level = logger_config.config['default']['level']
        self.default_tag = 'Global'
        self.sep = '|'
        self.simpy_env = simpy_env
        self.log_dir = output_dir
        self.entries = []
        self.buffer_writes: bool = logger_config.config['buffer_writes']
        self.split_logs: bool = logger_config.config['split_logs']                

    def get_log_file_name(self, tag=None):
        """Utilized to get the log pathname based upon the tag associated with a particular log

        :param tag: The tag associated with a particular log to identify it, defaults to None
        :type tag: _type_, optional
        :return: The pathname of the log file
        :rtype: str
        """
        if self.split_logs:
            node_id = re.search(r"^[0-9]+", tag) # Regex to pull first number (node_id)
            if node_id == None:
                return f'{self.log_dir}/logSimulator.txt'
            else:
                node_id = int(node_id.group()) # Gather matched section and convert to an int
                return f'{self.log_dir}/log{node_id}.txt'
        else:
            return f'{self.log_dir}/log.txt'

    def register(self, key: Hashable, level: LogLevel = None, tag: str = None):
        """Registers a sublogger to the LureLogger class

        :param key: Key for the sublogger
        :type key: Hashable
        :param level: Logging level of this logger, defaults to None
        :type level: LogLevel, optional
        :param tag: Tag associated with this logger, defaults to None
        :type tag: str, optional
        """
        l = level
        t = tag
        if l is None:
            l = self.default_level
        if tag is None:
            t = self.default_tag
        self.config[key] = { 'level': l, 'tag': t }

    def log(self, level: LogLevel, key: Hashable, msg: str):
        """Logs the given information in the log file

        :param level: The logging level
        :type level: LogLevel
        :param key: The logger key
        :type key: Hashable
        :param msg: Message to log
        :type msg: str
        """
        live_logging = 1 # Experimental!! 1 = live_log, 0 = cummulative_log

        write_log = False
        try:
            config = self.config[key]
        except KeyError:
            config = { 'level': self.default_level, 'tag': self.default_tag }
        
        try:
            tag = config['tag']
        except KeyError:
            tag = self.default_tag

        try:
            if level >= config['level']:
                write_log = True
        except KeyError:
            if level >= self.default_level:
                write_log = True
  
        if write_log:
            entry = f'{level}{self.sep}{self.simpy_env.now}{self.sep}{tag}{self.sep}{msg}\n'
            if self.buffer_writes:
                self.entries.append(entry)
            else:
                with open(self.get_log_file_name(tag=tag), 'a') as f:
                    f.write(entry)

    def close(self):
        if not self.buffer_writes:
            pass
            # for file in self.log_file.values():
            #     file.close()
            # self.log_file.close()
        elif len(self.entries) > 0:
            with open(self.get_log_file_name(), 'w') as f:
                f.writelines(self.entries)

class Loggable:
    """Determines if a class can be logged. Methods are called within a loggable class to log that data at specified method level 
    """

    def register_log(self, logger: LureLogger, log_level: LogLevel, tag: str):
        self.logger = logger
        self.logger.register(key=repr(self), level=log_level, tag=tag)

    def debug(self, msg: str):
        self.logger.log(level=LogLevel.DEBUG, key=repr(self), msg=msg)

    def info(self, msg: str):
        self.logger.log(level=LogLevel.INFO, key=repr(self), msg=msg)

    def warning(self, msg: str):
        self.logger.log(level=LogLevel.WARNING, key=repr(self), msg=msg)

    def error(self, msg: str):
        self.logger.log(level=LogLevel.ERROR, key=repr(self), msg=msg)

    def critical(self, msg: str):
        self.logger.log(level=LogLevel.CRITICAL, key=repr(self), msg=msg)