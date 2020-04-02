"""Simple UDP server to response server-search requests from devices"""

import json

from socketserver import BaseRequestHandler


class ServerSearchHandler(BaseRequestHandler):
    """Handle server search UDP requests from devices"""

    def handle(self):
        app, log, ip, socket = self.server.app, self.server.app.log, self.client_address[0], self.request[1]
        try:
            request = json.loads(self.request[0].decode())
            plugin, action = request['plugin'], request['action']
            uin, name, role = request['uin'], request['name'], request['role']
        except UnicodeDecodeError:
            log.warning('Unicode decoding error in UDP request')
        except json.JSONDecodeError as e:
            log.warning('JSON decoding error in UDP request: {}'.format(e))
        except KeyError as e:
            log.warning('Key not found in JSON (UDP request): {}'.format(e))
        else:
            if plugin == 'search' and action == 'request':
                app.dm.update_device(uin, ip, name, role)
                info = app.conf['self']
                response = json.dumps(dict(plugin='search', action='response', role='server',
                                           uin=info['uin'], name=info['name']))
                res = socket.sendto(response.encode(), self.client_address)
