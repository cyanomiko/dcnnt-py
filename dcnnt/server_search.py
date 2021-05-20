"""Simple UDP server to response server-search requests from devices"""

import json
from base64 import b64decode, b64encode
from threading import Thread
from socketserver import BaseRequestHandler

from .common import decrypt, encrypt, derive_key


class ServerSearchHandler(BaseRequestHandler):
    """Handle server search UDP requests from devices"""

    @staticmethod
    def unpack_raw_request(raw):
        """Unpack raw JSON-encoded data from UDP datagram"""
        request = json.loads(raw.decode())
        plugin, action, uin, name, role = map(request.pop, ('plugin', 'action', 'uin', 'name', 'role'))
        pair_data = request.get('pair')
        return plugin, action, uin, name, role, pair_data

    def handle(self):
        app, log, ip, socket = self.server.app, self.server.app.log, self.client_address[0], self.request[1]
        try:
            plugin, action, uin, name, role, pair_data = self.unpack_raw_request(self.request[0])
        except UnicodeDecodeError:
            log.warning('Unicode decoding error in UDP request')
        except json.JSONDecodeError as e:
            log.warning('JSON decoding error in UDP request: {}'.format(e))
        except KeyError as e:
            log.warning('Key not found in JSON (UDP request): {}'.format(e))
        else:
            if plugin == 'search' and action in 'request':
                pairing_code = getattr(self.server, 'pairing_code', None)
                info = app.conf['self']
                app.dm.update_device(uin, ip, name, role)
                if pairing_code and pair_data:
                    password = decrypt(b64decode(pair_data), derive_key(pairing_code + str(info['uin']))).decode()
                    if app.dm.update_device_password(uin, password):
                        Thread(name='Thread-UDP-Server-Shutdown', target=self.server.shutdown).start()
                        self.server.paired_uin = uin
                resp_data = dict(plugin='search', action='response', role='server', uin=info['uin'], name=info['name'])
                if pairing_code:
                    resp_data['pair'] = b64encode(encrypt(str(info['password']).encode(),
                                                          derive_key(pairing_code + str(uin)))).decode()
                response = json.dumps(resp_data)
                res = socket.sendto(response.encode(), self.client_address)
