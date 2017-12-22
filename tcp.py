import socket
from Communication.exceptions import *

class Tcp:
    def __init__(self, addr = None, port = 1234, timeout = None, encoding = 'utf8', decoding = None):
        self.__socket = None
        self.__addr = addr
        self.__port = Tcp.check_port(port)
        self.__timeout = timeout
        self.__encoding = encoding
        self.__decoding = decoding
        self.__recbuff = b''
        self.__bufsize = 4096
        if self.__addr != None:
            self.connect()

    def connect(self, addr = None, port = None):
        if self.connected:
            if addr == self.__addr and port == self.__port:
                return
            seld.disconnect()
        if addr != None:
            self.__addr = addr
        elif self.__addr == None:
            raise ValueError('Address not specified.')
        if port != None:
            self.__port = Tcp.check_port(port)
        self.__socket = socket.create_connection((self.__addr, self.__port), self.__timeout)

    def disconnect(self):
        if self.connected:
            self.__socket.close()
            self.__socket = None
            self.__recbuff = b''

    def read(self, size):
        if self.__socket == None: raise PortClosedError('Operation on closed port (read).')
        while len(self.__recbuff) < size:
            v = self.__socket.recv(self.__bufsize)
            if not v:
                raise ConnectionBrokenError()
            self.__recbuff += v
        ret = self.__recbuff[0:size]
        if len(self.__recbuff) > size:
            self.__recbuff = self.__recbuff[size:]
        else:
            self.__recbuff = b''
        if self.__decoding != None:
            ret = str(ret, self.__decoding)
        return ret

    def write(self, value):
        if self.__socket == None: raise PortClosedError('Operation on closed port (write).')
        value = bytes(value, self.__encodings)
        sent = 0
        all = len(value)
        while sent != all:
            v = self.__socket.send(value[sent:])
            if v == 0:
                raise ConnectionBrokenError()
            sent += v
        return sent

    @property
    def connected(self):
        return self.__socket != None

    @property
    def timeout(self):
        return self.__timeout
    @timeout.setter
    def timeout(self, value):
        if self.__socket != None:
            self.__socket.settimeout(value)
        self.__timeout = value

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.disconnect()
        return False

    def __repr__(self):
        if self.connected:
            state = '{}, {}'.format(self.__addr, self.__port)
        else:
            state = 'disconnected'
            if self.__addr != None:
                state += '[{}, {}]'.format(self.__addr, self.__port)
        return '<Tcp({}) at {:X}>'.format(state, id(self))

    open = connect
    close = disconnect

    @staticmethod
    def check_port(port):
        if not isinstance(port, int):
            raise TypeError('Port has to be int, {} given.'.format(type(port)))
        if port < 0 or port > 65535:
            raise ValueError('Port has to be in range 0 to 65536, {} given.'.format(port))
        return port
