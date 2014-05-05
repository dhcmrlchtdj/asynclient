#!/usr/bin/env python3

from asynclient import ac

@ac.coro
def get(url):
    # waiting for ``ac.get``
    resp = yield from ac.get(url)
    print(resp.body)

ac.run(get("google.com"))
