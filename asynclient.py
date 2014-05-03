#!/usr/bin/env python3

__version__ = "0.2.0"
__all__ = [
    "co",
    "run",
    "stop",
    "close",
    "fetch",
]


from urllib.parse import urlparse
import asyncio
import io




co = asyncio.coroutine

loop = asyncio.get_event_loop()

run = loop.run_until_complete
stop = loop.stop
close = loop.close




class HTTPRequest:
    def __init__(self, url, method="GET", headers=None, body=b"", *,
                 ua="asynclient/"+__version__):
        self.url = ("http://" + url) if "://" not in url else url
        self._parse_url()
        self.method = method
        self.headers = {
            "Accept-Encoding": "identity",
            "Connection": "close",
            "Host": self.netloc,
            "User-Agent": ua,
        }
        if headers:
            self.headers.update(headers)
        self.body = body.encode() if isinstance(body, str) else body
        self.req = None


    def _parse_url(self):
        parts = urlparse(self.url)
        self.netloc = parts.netloc
        ssl = parts.scheme == "https"
        self.port = parts.port or (443 if ssl else 80)
        path = parts.path or "/"
        self.path = "{}?{}".format(path, parts.query) if parts.query else path


    @property
    def request(self):
        if not self.req:
            lines = ["{} {} HTTP/1.0".format(self.method, self.path)]
            lines.extend(("{}: {}".format(k, v))
                         for k, v in self.headers.items())
            lines.extend(("", ""))
            self.req = io.BytesIO("\r\n".join(lines).encode())
            self.req.write(self.body)
        return self.req.getvalue()




class HTTPResponse:
    def __init__(self, request, code, headers, body):
        self.request = request
        self.code = code
        self.headers = headers
        self.body = body




class HTTPConnection:
    def __init__(self, url):
        self.url = url
        self.max_redirects = 5


    @co
    def get_response(self):
        redirect = 0
        while redirect < self.max_redirects:
            self.request = HTTPRequest(self.url)
            yield from self._connect()
            yield from self._send_request()
            resp = yield from self._get_response()

            if 200 <= resp.code < 300:
                return resp
            elif 300 <= resp.code < 400:
                self.url = resp.headers.get("location")
            else:
                raise Exception("status code '{}'".format(resp.code))

            redirect+=1
        else:
            raise Exception("redirect")


    @co
    def _connect(self):
        self.reader, self.writer = yield from asyncio.open_connection(
            self.request.netloc, self.request.port)


    @co
    def _send_request(self):
        self.writer.write(self.request.request)
        yield from self.writer.drain()


    @co
    def _get_response(self):
        r = self.reader

        @co
        def getline():
            return (yield from r.readline()).decode().rstrip()

        status_line = yield from getline()
        status_parts = status_line.split(None, 2)
        if len(status_parts) != 3 or not status_parts[1].isdigit():
            raise Exception(status_line)
        http_version, status, reason = status_parts
        status = int(status)

        headers = {}
        while True:
            header_line = yield from getline()
            if not header_line:
                break
            key, value = header_line.split(":", 1)
            headers[key.lower()] = value.lstrip()

        if "content-length" in headers:
            nbytes = int(headers["content-length"])
            body = yield from r.read(nbytes)
        elif headers.get("transfer-encoding", "") == "chunked":
            body = yield from self._chunked_handler()
        else:
            body = yield from r.read()

        return HTTPResponse(self.request, status, headers, body)


    @co
    def _chunked_handler(self):
        r = self.reader
        body = io.BytesIO()
        while True:
            size_header = yield from r.readline()
            parts = size_header.split(b";")
            size = int(parts[0], 16)
            if not size:
                break
            else:
                block = yield from r.readexactly(size)
                assert len(block) == size, (len(block), size)
                body.write(block)
            crlf = yield from r.readline()
            assert crlf == b'\r\n', repr(crlf)
        return body.getvalue()




@co
def fetch(url):
    conn = HTTPConnection(url)
    data = yield from conn.get_response()
    return data




if __name__ == '__main__':
    @co
    def get(url):
        data = yield from fetch(url)
        print(data.body)

    run(get("google.com"))
