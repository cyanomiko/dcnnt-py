import json

class RPCObject:
    """Just group of other classes"""
    __slots__ = ()


class RPCError(BaseException, RPCObject):
    """JSON-RPC 2.0 error object"""
    __slots__ = 'code', 'message', 'data'

    def __init__(self, code, message='error', data=None):
        self.code, self.message, self.data = code, message, data

    def __repr__(self):
        return '<JSON-RPC 2.0 Error [{}]: {} - "{}">'.format(self.code, self.message, self.data)

    def to_dict(self):
        """Convert to JSON-RPC 2.0 dictionary"""
        d = dict(code=self.code, message=self.message)
        if self.data is not None:
            d['data'] = self.data
        return d

    def add_data(self, data):
        """Create copy of object with data added"""
        return type(self).__call__(self.code, self.message, data)

    @classmethod
    def from_dict(cls, d):
        """Create RPCRequest object from dictionary"""
        return cls(d['code'], d['message'], d.get('data'))


PARSE_ERROR = RPCError(-32700, 'Parse error')
INVALID_REQUEST_ERROR = RPCError(-32600, 'Invalid Request')
METHOD_NOT_FOUND_ERROR = RPCError(-32601, 'Method not found')
INVALID_PARAMS_ERROR = RPCError(-32602, 'Invalid params')
INTERNAL_ERROR = RPCError(-32603, 'Internal error')
SERVER_ERROR = RPCError(-32000, 'Server error')


class RPCRequest(RPCObject):
    """JSON-RPC 2.0 request/notification object"""
    __slots__ = 'id', 'method', 'params'

    def __init__(self, method, params, id=None):
        assert isinstance(method, str), '"method" MUST be str'
        assert isinstance(params, (tuple, list, dict)) or params is None, '"params" MUST be tuple, list, dict or None'
        assert isinstance(id, (int, str)) or id is None, '"id" MUST be int, str or None'
        self.method, self.params, self.id = method, params, id

    def __repr__(self):
        return f'<JSON-RPC 2.0 Request [{self.id}]: {self.method}({self.params})>'

    def to_dict(self):
        """Convert to JSON-RPC 2.0 dictionary"""
        d = dict(jsonrpc='2.0', method=self.method, params=self.params)
        if self.id is not None:
            d['id'] = self.id
        return d

    @classmethod
    def from_dict(cls, d):
        """Create RPCRequest object from dictionary"""
        try:
            return cls(d['method'], d['params'], d.get('id'))
        except (KeyError, AssertionError) as e:
            raise INVALID_REQUEST_ERROR.add_data('{}: {}'.format(type(e), str(e)))


class RPCResponse(RPCObject):
    """JSON-RPC 2.0 response object"""
    __slots__ = 'id', 'result', 'error'

    def __init__(self, id, result):
        assert isinstance(id, (int, str)) or id is None, '"id" MUST be int, str or None'
        self.id = id
        if isinstance(result, RPCError):
            self.error, self.result = result, None
        else:
            self.error, self.result = None, result

    def __repr__(self):
        return f'<JSON-RPC 2.0 Request [{self.id}]: {self.error if self.result is None else self.result}>'

    def to_dict(self):
        """Convert to JSON-RPC 2.0 dictionary"""
        d = dict(jsonrpc='2.0', id=self.id)
        if self.error is not None:
            d['error'] = self.error.to_dict()
        if self.result is not None:
            d['result'] = self.result
        return d

    @classmethod
    def from_dict(cls, d):
        """Create RPCRequest object from dictionary"""
        try:
            result = d.get('result')
            error = d.get('error')
            if (result is not None and error is not None) or (result is None and error is None):
                raise INVALID_REQUEST_ERROR.add_data('MUST contain result XOR error')
            return cls(d['id'], result if error is None else RPCError.from_dict(error))
        except (KeyError, AssertionError) as e:
            raise INVALID_REQUEST_ERROR.add_data('{}: {}'.format(type(e), str(e)))


class RPCDispatcher:
    """Get decoded requests and return results (success or error) from corresponding methods"""

    def __init__(self, methods):
        self.methods = methods if isinstance(methods, dict) else {func.__name__: func for func in methods}

    def dispatch(self, request):
        """Check if request is correct, execute RPC method and return response"""
        func = self.methods.get(request.method)
        if func is None:
            return None if request.id is None else RPCResponse(request.id, METHOD_NOT_FOUND_ERROR)
        else:
            try:
                result = func(**request.params) if isinstance(request.params, dict) else func(*request.params)
                return None if request.id is None else RPCResponse(request.id, result)
            except TypeError as e:
                return None if request.id is None else RPCResponse(request.id, INVALID_PARAMS_ERROR.add_data(str(e)))
            except BaseException as e:
                return None if request.id is None else RPCResponse(request.id, INTERNAL_ERROR.add_data(str(e)))


class RPCSerializer:
    """Methods to serialize and deserialize JSON-RPC objects"""

    def __init__(self, ensure_ascii=True, length_bytes=None, order='big', separator=b''):
        self.ensure_ascii, self.length_bytes, self.separator, self.order = ensure_ascii, length_bytes, separator, order

    def to_bytes(self, obj):
        """Serialize JSON-RPC object to bytes"""
        try:
            return json.dumps(obj.to_dict(), separators=(',', ':'), ensure_ascii=self.ensure_ascii).encode()
        except BaseException:
            packed = json.dumps(RPCResponse(obj.id, INTERNAL_ERROR),
                                separators=(',', ':'), ensure_ascii=self.ensure_ascii).encode()
            return b''.join((len(packed).to_bytes(self.length_bytes, self.order) if self.length_bytes else b'',
                            packed, self.separator))

    def from_bytes(self, raw):
        """Extract JSON-RPC objects from byte string"""
        res = list()
        try:
            data = json.loads(raw.decode())
            if not isinstance(data, list):
                data = (data, )
            for d in data:
                try:
                    if not isinstance(d, dict):
                        res.append(INVALID_REQUEST_ERROR.add_data('Not object'))
                    if 'jsonrpc' not in d:
                        res.append(INVALID_REQUEST_ERROR.add_data('No "jsonrpc" key'))
                    if d['jsonrpc'] != '2.0':
                        res.append(INVALID_REQUEST_ERROR.add_data('JSON-RPC version != 2.0'))
                    if 'method' in d:
                        res.append(RPCRequest.from_dict(d))
                    elif 'result' in d or 'error' in d:
                        res.append(RPCResponse.from_dict(d))
                    else:
                        res.append(INVALID_REQUEST_ERROR.add_data('Not request or response'))
                except RPCError as e:
                    res.append(e)
                except BaseException as e:
                    res.append(SERVER_ERROR)
        except json.JSONDecodeError:
            res.append(PARSE_ERROR.add_data('JSON error'))
        except UnicodeDecodeError:
            res.append(PARSE_ERROR.add_data('UTF-8 error'))
        except BaseException:
            res.append(SERVER_ERROR)
        return res
