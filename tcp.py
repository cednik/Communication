import socket
from Communication.exceptions import *
from codecs import getincrementalencoder, getincrementaldecoder, IncrementalEncoder, IncrementalDecoder

class transparent_coder(IncrementalEncoder, IncrementalDecoder):
    def encode(self, object, final = False):
        return object
    def decode(self, object, final = False):
        return object

class Client:
    def __init__(self, addr = None, port = 1234, timeout = None, encoding = 'utf8', decoding = None):
        self.__socket = None
        self.__addr = addr
        self.__port = Client.check_port(port)
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
            self.__port = Client.check_port(port)
        self.__socket = socket.create_connection((self.__addr, self.__port), self.__timeout)
        self.__readable = True
        self.__writable = True

    def disconnect(self):
        if self.connected:
            self.shutdown(True, True)
            self.__socket.close()
            self.__socket = None
            self.__init_recbuff()

    def shutdown(self, write = True, read = False):
        if self.__socket == None: raise PortClosedError('Operation on closed port (read).')
        if write:
            how = socket.SHUT_RDWR if read else socket.SHUT_WR
        elif read:
            how = socket.SHUT_RD
        else:
            return
        self.__readable &= ~read
        self.__writable &= ~write
        self.__socket.shutdown(how)
            

    def read(self, size = 1):
        if self.__socket == None: raise PortClosedError('Operation on closed port (read).')
        if not self.__readable: raise ConnectionBrokenError()
        while len(self.__recbuff) < size:
            try:
                v = self.__socket.recv(self.__bufsize)
            except (socket.timeout, BlockingIOError):
                break
            except ConnectionResetError:
                self.__readable = False
                raise
            if not v:
                self.__readable = False
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
        if not self.__writable: raise ConnectionBrokenError()
        if self.__force_encode or isinstance(value, str):
            value = self.__encoder.encode(value)
        else:
            value = bytes(value)
        sent = 0
        all = len(value)
        while sent != all:
            v = self.__socket.send(value[sent:])
            if v == 0:
                self.__writable = False
                raise ConnectionBrokenError()
            sent += v
        return sent

    @property
    def connected(self):
        return self.__socket != None

    @property
    def readable(self):
        return self.__readable

    @property
    def writable(self):
        return self.__writable

    @property
    def address(self):
        return self.__addr

    @property
    def port(self):
        return self.__port

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
        self.__encoder = Client.resolve_coder(value, getincrementalencoder)
        self.__force_encode = self.__encoder == value

    @property
    def decoder(self):
        return self.__decoder
    @decoder.setter
    def decoder(self, value):
        self.__decoder = Client.resolve_coder(value, getincrementaldecoder)

    @property
    def read_type(self):
        return b'' if isinstance(self.__decoder, transparent_coder) else ''

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
        return '<tcp.Client({}) at 0x{:08X}>'.format(state, id(self))

    open = connect
    close = disconnect

    def _from_server(self, socket, addr, timeout):
        self.__socket = socket
        self.__addr = addr
        self.__readable = True
        self.__writable = True
        self.timeout = timeout
        return self

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


class Server:
    def __init__(self, addr = '', port = 1234, timeout = None, family = socket.AF_INET, type = socket.SOCK_STREAM, proto = 0, max_con = 1, client_timeout = None, encoding = 'utf8', decoding = None):
        self.__port = Client.check_port(port)
        self.__client_timeout = client_timeout
        self.__encoding = encoding
        self.__decoding = decoding
        self.__socket = socket.socket(family, type, proto)
        self.__socket.bind((addr, self.__port))
        self.__socket.listen(max_con)
        self.__socket.settimeout(timeout)

    def accept(self):
        try:
            sock, addr = self.__socket.accept()
        except (socket.timeout, BlockingIOError):
            return None
        except:
            raise
        else:
            return Client(port = self.__port, encoding = self.__encoding, decoding = self.__decoding)._from_server(sock, addr, self.__client_timeout)

    def close(self):
        self.__socket.close()
