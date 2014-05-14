#!/usr/bin/env python3

from asynclient import ac

ac.config(
    connect_timeout=1,
    request_timeout=10
)

@ac.coro
def get(url):
    resp = yield from ac.get(url)
    print(resp.body)

ac.run(get("google.com"))
