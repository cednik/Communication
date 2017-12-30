import socket
from Communication.exceptions import *
from codecs import getincrementalencoder, getincrementaldecoder, IncrementalEncoder, IncrementalDecoder

class transparent_coder(IncrementalEncoder, IncrementalDecoder):
    def encode(self, object, final):
        return object
    def decode(self, object, final):
        return object

class Tcp:
    def __init__(self, addr = None, port = 1234, timeout = None, encoding = 'utf8', decoding = None):
        self.__socket = None
        self.__addr = addr
        self.__port = Tcp.check_port(port)
        self.__timeout = timeout
        self.encoder = encoding
        self.decoder = decoding
        self.__init_recbuff()
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
            self.__init_recbuff()

    def read(self, size = 1):
        if self.__socket == None: raise PortClosedError('Operation on closed port (read).')
        while len(self.__recbuff) < size:
            try:
                v = self.__socket.recv(self.__bufsize)
            except socket.timeout:
                break
            if not v:
                raise ConnectionBrokenError()
            self.__recbuff += self.__decoder.decode(v)
        ret = self.__recbuff[0:size]
        if len(self.__recbuff) > size:
            self.__recbuff = self.__recbuff[size:]
        else:
            self.__init_recbuff()
        return ret

    def write(self, value):
        if self.__socket == None: raise PortClosedError('Operation on closed port (write).')
        if self.__force_encode or isinstance(value, str):
            value = self.__encoder.encode(value)
        else:
            value = bytes(value)
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

    @property
    def encoder(self):
        return self.__encoder
    @encoder.setter
    def encoder(self, value):
        self.__encoder = Tcp.resolve_coder(value, getincrementalencoder)
        self.__force_encode = self.__encoder == value

    @property
    def decoder(self):
        return self.__decoder
    @decoder.setter
    def decoder(self, value):
        self.__decoder = Tcp.resolve_coder(value, getincrementaldecoder)

    @property
    def read_type(self):
        return b'' if self.__decoder == None else ''

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
        return '<Tcp({}) at 0x{:08X}>'.format(state, id(self))

    open = connect
    close = disconnect

    def __init_recbuff(self):
        self.__recbuff = self.read_type

    @staticmethod
    def check_port(port):
        if not isinstance(port, int):
            raise TypeError('Port has to be int, {} given.'.format(type(port)))
        if port < 0 or port > 65535:
            raise ValueError('Port has to be in range 0 to 65536, {} given.'.format(port))
        return port

    @staticmethod
    def resolve_coder(codings, getter):
        if codings == None: return transparent_coder()
        if isinstance(codings, str): return getter(codings)()
        return codings
