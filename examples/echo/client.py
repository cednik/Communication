import sys, os.path, traceback
sys.path.append(os.path.join(*(3 * ['..'])))

from Communication.tcp import Client

tcp = Client('localhost', 1234, timeout = 2, encoding = 'utf8', decoding = None)

if tcp.connected:
    print('Connected')

    tcp.write([0, 128, 255])
    tcp.write('ahoj')

    while 1:
        try:
            if tcp.readable:
                read = tcp.read()
                if read:
                    if tcp.writable:
                        tcp.write(read)
                    print(read)
        except KeyboardInterrupt:
            break
        except Exception:
            print('Exception in user code:')
            print('-'*60)
            traceback.print_exc(file=sys.stdout)
            print('-'*60)
        while tcp.was_error:
            print('Error in tcp:')
            print('-'*60)
            print(repr(tcp.error))
            print('-'*60)
    tcp.close()
    print('\n\nclosed')
else:
    print('Connection could not be made:\n{}'.format(tcp.error))
