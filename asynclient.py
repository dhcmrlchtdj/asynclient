#!/usr/bin/env python3

"""
    asynclient
    ~~~~~~~~~~

    An asynchronous HTTP client.

    :copyright: (c) 2014 by niris.
"""

from asyncio import coroutine
from functools import partial
from urllib.parse import urlparse
import asyncio
import concurrent.futures
import io
import logging



__version__ = "0.2.6"
__author__ = "niris <nirisix@gmail.com>"
__description__ = "An asynchronous HTTP client."
__all__ = ["ac"]




logging.basicConfig(level=logging.INFO)




class ACError(Exception): pass
class ACTimeout(ACError, TimeoutError): pass
class ACHTTPError(ACError): pass




class URL:
    def __init__(self, url):
        self.url = ("http://" + url) if "://" not in url else url

        parts = urlparse(self.url)

        self.netloc = parts.netloc

        ssl = parts.scheme == "https"
        self.port = parts.port or (443 if ssl else 80)

        path = parts.path or "/"
        self.path = "{}?{}".format(path, parts.query) if parts.query else path




class HTTPHeaders(dict): pass




class HTTPRequest:
    def __init__(self, url, method="GET", headers=None, body=b""):
        self.url = url
        self.method = method
        self.path = url.path
        self.headers = {
            "Accept-Encoding": "identity",
            "Connection": "close",
            "Host": url.netloc,
        }
        self.headers.update(headers)
        self.body = body.encode() if isinstance(body, str) else body


    @property
    def request(self):
        if not self._request:
            lines = ["{} {} HTTP/1.0".format(self.method, self.path)]
            lines.extend(("{}: {}".format(k, v))
                         for k, v in self.headers.items())
            lines.extend(("", ""))

            self._request = io.BytesIO("\r\n".join(lines).encode())
            self._request.write(self.body)

        return self._request.getvalue()




class HTTPResponse:
    def __init__(self, code, reason, headers, body):
        self.code = code
        self.reason = reason
        self.headers = headers
        self.body = body




class HTTPConnection:
    def __init__(self, url, *,
                 timeout=None, follow_redirects=True, max_redirects=5,
                 ua="asynclient/"+__version__,
                 **kwds):
        self.url = URL(url)

        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects

        headers = kwds.setdefault("headers", {})
        headers.setdefault("User-Agent", ua)
        self.settings = kwds


    @coroutine
    def get_response(self):
        redirect = 0
        while redirect < self.max_redirects:
            yield from self._connect()

            request = HTTPRequest(self.url, **self.settings)
            yield from self._send_request(request)

            resp = yield from self._get_response()

            if 200 <= resp.code < 300:
                return resp
            elif 300 <= resp.code < 400:
                if self.follow_redirects:
                    self.url = URL(resp.headers.get("location"))
                else:
                    return resp
            else:
                raise ACHTTPError(
                    "HTTP Error {}: {}".format(resp.code, resp.reason))

            redirect+=1
        else:
            raise ACError("redirect")


    @coroutine
    def _connect(self):
        fut = asyncio.open_connection(self.url.netloc, self.url.port)

        if self.timeout is not None:
            fut = asyncio.wait_for(fut, self.timeout)

        try:
            self.reader, self.writer = yield from fut
        except concurrent.futures._base.TimeoutError as e:
            raise ACTimeout("connect timeout")


    @coroutine
    def _send_request(self, request):
        w = self.writer
        w.write(request.request)
        yield from w.drain()


    @coroutine
    def _get_response(self):
        r = self.reader

        @coroutine
        def getline():
            return (yield from r.readline()).decode().rstrip()

        status_line = yield from getline()
        status_parts = status_line.split(None, 2)
        if len(status_parts) != 3 or not status_parts[1].isdigit():
            raise ACError(status_line)
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

        return HTTPResponse(status, reason, headers, body)


    @coroutine
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




class CONFIGURE:
    def __init__(self):
        self.keys = (
            "method",
            "headers",
            "body",
            "ua",
            "timeout",
            "follow_redirects",
            "max_redirects",
        )
        self.settings = {}


    def _update(self, old, new):
        old.update({
            key: val
            for key, val in new.items()
            if key in self.keys
        })


    def __call__(self, **settings):
        self._update(self.settings, settings)


    def update(self, **settings):
        new_settings = self.settings.copy()
        self._update(new_settings, settings)
        logging.info("connection config: %s", new_settings)
        return new_settings




class Asynclient:
    def __init__(self, max_tasks=10, *, loop=None):
        _loop = loop or asyncio.get_event_loop()

        self.loop = _loop
        self.run = _loop.run_until_complete
        self.stop = _loop.stop
        self.close = _loop.close

        self.governor = asyncio.Semaphore(max_tasks, loop=_loop)

        self.async = partial(asyncio.async, loop=_loop)
        self.gather = partial(asyncio.gather, loop=_loop)
        self.sleep = partial(asyncio.sleep, loop=_loop)

        self.config = CONFIGURE()


    def coro(self, gen):
        return coroutine(gen)


    @coroutine
    def _fetch(self, url, **settings):
        settings = self.config.update(**settings)
        conn = HTTPConnection(url, **settings)
        with (yield from self.governor):
            return (yield from conn.get_response())


    @coroutine
    def get(self, url, **settings):
        settings["method"] = "GET"
        return (yield from self._fetch(url, **settings))


    @coroutine
    def post(self, url, **settings):
        settings["method"] = "POST"
        return (yield from self._fetch(url, **settings))



ac = Asynclient()



def main():
    import argparse
    ARGS = argparse.ArgumentParser(description=__description__)
    ARGS.add_argument("url")
    args = ARGS.parse_args()

    @ac.coro
    def print_body(url):
        resp = yield from ac.get(url)
        print(resp.body)
    ac.run(print_body(args.url))


if __name__ == "__main__":
    main()
