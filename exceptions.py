class ConnectionBrokenError(RuntimeError):
    def __init__(self, msg = 'Connection broken.'):
        super().__init__(msg)

class PortClosedError(RuntimeError):
    def __init__(self, msg = 'Operation on closed port.'):
        super().__init__(msg)

class DeadlockError(RuntimeError):
    def __init__(self, msg):
        super().__init__(msg)
