class ConnectionBrokenError(RuntimeError):
    def __init__(msg = 'Connection broken.'):
        RuntimeError.__init__(msg)

class PortClosedError(RuntimeError):
    def __init__(msg = 'Operation on closed port.'):
        RuntimeError.__init__(msg)
