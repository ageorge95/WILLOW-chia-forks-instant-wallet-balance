from logging import basicConfig,\
    INFO, DEBUG, WARNING, ERROR, CRITICAL,\
    Formatter,\
    StreamHandler, FileHandler, Handler,\
    getLogger
from sys import stdout
from queue import Queue
from os import path,\
    system
from json import load,\
    dump
import sys
from _00_config import initial_config
from sqlite3 import connect

class db_wrapper_v1():
    def connect_to_db(self,
                      db_filepath):
        self._conn = connect(db_filepath)
        self._dbcursor = self._conn.cursor()

    def get_coins_by_puzzlehash(self,
                                puzzlehash):
        self._dbcursor.execute("SELECT timestamp, amount, spent_index FROM coin_record WHERE puzzle_hash=? ORDER BY timestamp DESC", (puzzlehash,))
        return self._dbcursor.fetchall()

    def get_last_win_time(self,
                          puzzlehash):
        self._dbcursor.execute("SELECT timestamp FROM coin_record WHERE puzzle_hash=? AND coinbase = 1 ORDER BY timestamp DESC LIMIT 1", (puzzlehash,))
        return self._dbcursor.fetchall()

class db_wrapper_v2():
    def connect_to_db(self,
                      db_filepath):
        self._conn = connect(db_filepath)
        self._dbcursor = self._conn.cursor()

    def get_coins_by_puzzlehash(self,
                                puzzlehash):
        self._dbcursor.execute("SELECT timestamp, amount, spent_index FROM coin_record WHERE puzzle_hash=? ORDER BY timestamp DESC", (bytes.fromhex(puzzlehash),))
        return self._dbcursor.fetchall()

    def get_last_win_time(self,
                          puzzlehash):
        self._dbcursor.execute("SELECT timestamp FROM coin_record WHERE puzzle_hash=? AND coinbase = 1 ORDER BY timestamp DESC LIMIT 1", (bytes.fromhex(puzzlehash),))
        return self._dbcursor.fetchall()

def db_wrapper_selector(version: int):
    if version == 1:
        return db_wrapper_v1
    elif version == 2:
        return db_wrapper_v2
    else:
        return None

def configure_logger():
    class CustomFormatter(Formatter):
        grey = "\x1b[38;21m"
        yellow = "\x1b[33;21m"
        red = "\x1b[31;21m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format = '%(asctime)s,%(msecs)d %(levelname)-4s [%(filename)s:%(lineno)d -> %(name)s - %(funcName)s] ___ %(message)s'

        FORMATS = {
            DEBUG: grey + format + reset,
            INFO: grey + format + reset,
            WARNING: yellow + format + reset,
            ERROR: red + format + reset,
            CRITICAL: bold_red + format + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = Formatter(log_fmt)
            return formatter.format(record)

    ch = StreamHandler(stream=stdout)
    ch.setLevel(INFO)
    ch.setFormatter(CustomFormatter())
    fh = FileHandler("../runtime_log.log")
    fh.setLevel(INFO)
    fh.setFormatter(Formatter('%(asctime)s,%(msecs)d %(levelname)-4s [%(filename)s:%(lineno)d -> %(name)s - %(funcName)s] ___ %(message)s'))

    basicConfig(datefmt='%Y-%m-%d:%H:%M:%S',
                level=INFO,
                handlers=[
                    fh,
                    ch
                ])

class QueueHandler(Handler):
    """Class to send logging records to a queue
    It can be used from different threads
    The ConsoleUi class polls this queue to display records in a ScrolledText widget
    """
    # Example from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    # (https://stackoverflow.com/questions/13318742/python-logging-to-tkinter-text-widget) is not thread safe!
    # See https://stackoverflow.com/questions/43909849/tkinter-python-crashes-on-new-thread-trying-to-log-on-main-thread

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)

class configure_logger_and_queue():
    def __init__(self):
        
        system("color")  # enable color in the console

        super(configure_logger_and_queue, self).__init__()

        configure_logger()

        self._log = getLogger()

        # Create a logging handler using a queue
        self.log_queue = Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = Formatter('%(asctime)s %(levelname)-4s %(message)s')
        self.queue_handler.setFormatter(formatter)
        self._log.addHandler(self.queue_handler)

class config_handler():
    def __init__(self):
        super(config_handler, self).__init__()

        config_path = 'config_willow.json' if '_MEIPASS' in sys.__dict__ \
            else path.join(path.dirname(__file__), '../config_willow.json')

        if path.isfile(config_path):
            try:
                with open(config_path, 'r') as json_in_handle:
                    self.config = load(json_in_handle)
            except:
                self.config = initial_config
        else:
            self.config = initial_config
            with open(config_path, 'w') as json_out_handle:
                dump(self.config, json_out_handle, indent=2)