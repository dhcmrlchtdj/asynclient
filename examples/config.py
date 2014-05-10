#!/usr/bin/env python3

from asynclient import ac

ac.config(
    timeout=1,
    request_timeout=10
)

@ac.coro
def get(url):
    # waiting for ``ac.fetch``
    resp = yield from ac.get(url)
    print(resp.body)

ac.run(get("google.com"))
