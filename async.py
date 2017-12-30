import logging
from warnings import warn
import threading
from queue import Queue, Empty
from Communication.exceptions import *
import sys

def _get_logger(name):
    return logging.getLogger(__name__ + '.' + name)

class Async:

    class TimeoutWarning(UserWarning):
        def __init__(self, msg = ''):
            self.__msg = msg
        def __str__(self):
            return self.__msg

    class WriteRecord:
        def __init__(self, data, onWritten):
            self.data = data
            self.__onWritten = onWritten
            self.exception = None
            self.traceback = None
            self.sent = 0
            self.done = threading.Event()

        def _exception(self):
            (_, self.exception, self.traceback) = sys.exc_info()

        def onWritten(self):
            self.done.set()
            if self.__onWritten != None:
                self.__onWritten(self)

    class Transceiver:
        def __init__(self, transceiver):
            self._transceiver = transceiver

        @property
        def is_alive(self):
            return self._transceiver.thread.is_alive()

        @property
        def logger(self):
            return self._transceiver.log
    

    def __init__(self, interface, i_args = (), i_kwargs = {}, timeout = 1, onReceived = None, onError = None):
        self.__log = _get_logger('Async<0x{:08X}>'.format(id(self)))
        if timeout == None:
            raise ValueError('None timeout prevents Async from termination, unless some data arrives.')
        min_recommended_timeout = 0.1
        max_recommended_timeout = 2
        if timeout < min_recommended_timeout:
            warn(
                Async.TimeoutWarning(
                    'Too short timeout causes excessive processor cunsumption. Minimal recomended value is {} s ({} s passed).'.format(min_recommended_timeout, timeout)),
                stacklevel = 2)
        if timeout > max_recommended_timeout:
            warn(
                Async.TimeoutWarning(
                    'Too long timeout causes excessive delays when Async termination is required. Maximal recomended value is {} s ({} s passed).'.format(max_recommended_timeout, timeout)),
                stacklevel = 2)
        i_kwargs['timeout'] = timeout
        self.__interface = interface(*i_args, **i_kwargs)
        self.__exit = threading.Event()
        self.__onReceived = onReceived
        self.__onError = onError
        self.__connected = self.__interface.connected
        if self.__connected:
            self.__create_workers()

    def connect(self, *arg, **kwarg):
        self.__log.info('Connecting')
        if self.connected:
            self.disconnect()
        self.__interface.connect(*arg, **kwarg)
        self.__exit.clear()
        self.__create_workers()
        self.__connected = True

    def disconnect(self):
        if not self.connected: return
        self.__log.info('Disconnecting')
        self.__transmitter.queue.put(None)
        self.__log.debug('process_tx stop sent')
        self.__transmitter.queue.join()
        self.__log.debug('process_tx all sent')
        self.__exit.set()
        self.__log.debug('exit set')
        self.__transmitter.thread.join()
        self.__log.debug('process_tx joint')
        self.__receiver.thread.join()
        self.__log.debug('process_rx joint')
        self.__interface.disconnect()
        self.__log.debug('disconnected')
        self.__connected = False

    def read(self, size = 0, timeout = None):
        if not self.connected: raise PortClosedError('Operation on closed port (read).')
        rec = self.__interface.read_type
        available = self.__receiver.queue.qsize()
        if size < 1:
            size = available - size
            if size < 1:
                return rec
        block = timeout != None
        if block:
            if timeout <= 0:
                raise ValueError('Timeout has to be None or positive number, {} passed.'.format(timeout))
            if size > available:
                if threading.get_ident() == self.__receiver.thread.ident:
                    raise DeadlockError('Can not read more bytes then are waiting in receiver queue inside of onReceived callback ({} wanted, but only {} available].'.format(size, available))
                if not self.__receiver.thread.is_alive():
                    raise DeadlockError('Can not read more bytes then are waiting in receiver queue because process_rx thread terminates ({} wanted, but only {} available].'.format(size, available))
        while len(rec) < size:
            try:
                rec += self.__receiver.queue.get(block, timeout)
                self.__receiver.queue.task_done()
            except Empty:
                break
        return rec

    def write(self, value, onWritten = None):
        if not self.connected: raise PortClosedError('Operation on closed port (write).')
        if not self.__transmitter.thread.is_alive():
            raise ConnectionBrokenError('Transmitter thread terminates')
        rec = Async.WriteRecord(value, onWritten)
        self.__transmitter.queue.put(rec)
        return rec

    def flush(self):
        if not self.connected: raise PortClosedError('Operation on closed port (flush).')
        if threading.get_ident() == self.__transmitter.thread.ident:
            raise DeadlockError('Flush can not be called from onWritten callback.')
        if not self.__transmitter.thread.is_alive():
            raise DeadlockError('Can not longer transmit data, because process_tx thread terminates')
        self.__transmitter.queue.join()

    def available(self):
        if not self.connected: raise PortClosedError('Operation on closed port (available).')
        return self.__receiver.queue.qsize()

    @property
    def connected(self):
        return self.__connected

    @property
    def receiver(self):
        return Async.Transceiver(self.__receiver)

    @property
    def transmitter(self):
        return Async.Transceiver(self.__transmitter)

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.disconnect()
        return False

    def __repr__(self):
        return '<Async ' + repr(self.__interface)[1:]

    def __create_workers(self):
        name_prefix = repr(self) + '.'
        self.__receiver = self.__create_worker(self.__process_rx, name_prefix, 'process_rx')
        self.__receiver.thread.start()
        self.__transmitter = self.__create_worker(self.__process_tx, name_prefix, 'process_tx')
        self.__transmitter.thread.start()
    
    def __create_worker(self, worker, name_prefix, name):
        class Worker: pass
        Worker.queue = Queue()
        Worker.thread = threading.Thread(target = worker)
        Worker.thread.name = 'Thread ' + name_prefix + name
        Worker.log = logging.getLogger(self.__log.name + '.' + name)
        return Worker

    def __process_rx(self):
        self.__receiver.log.info('Receiver thread started')
        while not self.__exit.is_set():
            try:
                recv = self.__interface.read(1)
                if not recv:
                    continue
                self.__receiver.queue.put(recv)
            except Exception as e:
                self.__receiver.log.exception('Exception occured during receiving data')
                self.__process_exception(e)
                break
            if self.__onReceived != None:
                try:
                    self.__onReceived(self)
                except Exception as e:
                    self.__receiver.log.exception('Exception occured in user callback')
                    self.__process_user_exception(e)
        self.__receiver.log.info('Receiver thread finished')

    def __process_tx(self):
        self.__transmitter.log.info('Transmitter thread started')
        while 1:
            rec = self.__transmitter.queue.get()
            if rec == None:
                self.__transmitter.queue.task_done()
                self.__transmitter.log.debug('got stop command')
                break
            self.__transmitter.log.debug('got data')
            try:
                sent = self.__interface.write(rec.data)
                self.__transmitter.log.debug('data sent')
            except Exception:
                self.__transmitter.log.exception('Exception occured during sending data')
                rec._exception()
            else:
                rec.sent = sent
            finally:
                try:
                    rec.onWritten()
                except Exception as e:
                    self.__transmitter.log.exception('Exception occured in user callback')
                    self.__process_user_exception(e)
                else:
                    if rec.exception != None:
                        self.__process_exception(rec.exception)
                finally:
                    self.__transmitter.queue.task_done()
        self.__transmitter.log.info('Transmitter thread finished')

    def __process_user_exception(self, exception, recursion = 0):
        self.__process_exception(exception, recursion)

    def __process_exception(self, exception, recursion = 0):
        if self.__onError != None:
            try:
                self.__onError(self, exception)
            except Exception as e:
                self.__log.exception('Exception occured in user error callback')
                if recursion < 2:
                    self.__process_user_exception(e, recursion+1)

    open = connect
    close = disconnect