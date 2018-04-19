import sys, os.path, traceback
sys.path.append(os.path.join(*(3 * ['..'])))

from Communication.tcp import Server

server = Server('localhost', 1234, timeout = 0, client_timeout = 0, encoding = 'utf8', decoding = None)
clients = []

print('Listenning...')

while 1:
    try:
        client = server.accept()
        if client != None:
            clients.append(client)
            print('client {} connected.'.format(id(client)))
        closed = []
        for client in clients:
            if not client.readable:
                closed.append(client)
            else:
                read = client.read()
                if read:
                    print('from {} read {}'.format(id(client), read))
                    client.write(read)
        for client in closed:
            print('client {} closed.'.format(id(client)))
            clients.remove(client)
    except KeyboardInterrupt:
        break
    except Exception:
        print("Exception in user code:")
        print("-"*60)
        traceback.print_exc(file=sys.stdout)
        print("-"*60)
server.close()
for client in clients:
    client.close()
print('\n\nclosed')
