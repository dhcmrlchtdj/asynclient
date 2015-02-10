#!/usr/bin/env python3

"""
    asynclient
    ~~~~~~~~~~

    An asynchronous HTTP client.

    :copyright: (c) 2014 by niris.
"""

from asyncio import coroutine
from collections import namedtuple
from functools import partial
from urllib.parse import urlparse
import asyncio
import collections.abc
import concurrent.futures
import io
import logging




__version__ = "0.2.14"
__author__ = "niris <nirisix@gmail.com>"
__description__ = "An asynchronous HTTP client."
__all__ = ["ac", "Asynclient"]




logger = logging.getLogger(__name__)




class ACError(Exception): pass
class ACTimeout(ACError, TimeoutError): pass
class ACHTTPError(ACError): pass




URL = namedtuple("URL", ("url", "host", "port", "ssl", "netloc", "path"))

@coroutine
def parse_url(url):
    url = url if ("://" in url) else ("http://" + url)

    parts = urlparse(url)

    ssl = parts.scheme == "https"

    netloc = parts.netloc

    path = parts.path or "/"
    if parts.query:
        path = "%s?%s" % (path, parts.query)

    port = parts.port or (443 if ssl else 80)

    host = parts.hostname

    return URL(url, host, port, ssl, netloc, path)




class HTTPHeaders(collections.abc.MutableMapping):
    def __init__(self, mapping=None):
        self._d = {}
        if mapping:
            for k, v in mapping.items():
                self[k] = v


    def __getitem__(self, key):
        key = key.title()
        return self._d[key]


    def __setitem__(self, key, value):
        key = key.title()
        self._d[key] = value


    def __delitem__(self, key):
        key = key.title()
        del self._d[key]


    def __iter__(self):
        return iter(self._d)


    def __len__(self):
        return len(self._d)


    def __str__(self):
        return str(self._d)




class HTTPRequest:
    def __init__(self, url, method="GET", headers=None, body=b""):
        self.path = url.path
        self.method = method
        self.headers = HTTPHeaders({
            "accept-encoding": "identity",
            "connection": "close",
            "host": url.netloc,
        })
        self.headers.update(headers)
        self.body = body.encode() if isinstance(body, str) else body

        self._request = None


    @property
    def request(self):
        if not self._request:
            lines = ["%s %s HTTP/1.0" % (self.method, self.path)]
            lines.extend(("%s: %s" % (k, v))
                         for k, v in self.headers.items())
            lines.extend(("", ""))

            self._request = io.BytesIO("\r\n".join(lines).encode())
            self._request.write(self.body)

        logger.debug("request '%s'", self._request.getvalue())

        return self._request.getvalue()




class HTTPResponse:
    def __init__(self, code, reason, headers, body):
        self.code = code
        self.reason = reason
        self.headers = headers
        self.body = body




class HTTPConnection:
    def __init__(self, url, *,
                 loop=None,
                 connect_timeout=None, follow_redirects=True, max_redirects=5,
                 ua="asynclient/" + __version__,
                 **kwds):
        self.loop = loop or asyncio.get_event_loop()

        self.url = url

        self.connect_timeout = connect_timeout
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects

        headers = kwds.setdefault("headers", HTTPHeaders())
        headers.setdefault("user-agent", ua)
        self.settings = kwds


    @coroutine
    def get_response(self):
        url = yield from parse_url(self.url)
        redirect = 0
        while True:
            yield from self._connect(url)

            request = HTTPRequest(url, **self.settings)
            yield from self._send_request(request)

            resp = yield from self._get_response()

            if 200 <= resp.code < 300:
                return resp
            elif 300 <= resp.code < 400:
                if (not self.follow_redirects) or (redirect >= self.max_redirects):
                    return resp
                else:
                    redirect += 1
                    url = yield from parse_url(resp.headers.get("location"))
            else:
                raise ACHTTPError("HTTP Error %s: %s" % (resp.code, resp.reason))



    @coroutine
    def _connect(self, url):
        _loop = self.loop
        _timeout = self.connect_timeout

        fut = asyncio.open_connection(url.netloc, url.port, loop=_loop)

        if _timeout is not None:
            fut = asyncio.wait_for(fut, _timeout, loop=_loop)

        try:
            self.reader, self.writer = yield from fut
        except concurrent.futures._base.TimeoutError:
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
            logger.debug(status_line)
            raise ACError(status_line)
        http_version, status, reason = status_parts
        status = int(status)

        headers = HTTPHeaders()
        while True:
            header_line = yield from getline()
            if not header_line:
                break
            key, value = header_line.split(":", 1)
            headers[key] = value.lstrip()

        if "content-length" in headers:
            nbytes = int(headers["content-length"])
            body = yield from r.readexactly(nbytes)
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
            "connect_timeout",
            "request_timeout",
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

        _timeout = settings.pop("request_timeout", None)
        _loop = self.loop

        conn = HTTPConnection(url, loop=_loop, **settings)

        with (yield from self.governor):
            fut = conn.get_response()

            if _timeout is not None:
                fut = asyncio.wait_for(fut, _timeout, loop=_loop)

            try:
                return (yield from fut)
            except concurrent.futures._base.TimeoutError:
                raise ACTimeout("request timeout")


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
