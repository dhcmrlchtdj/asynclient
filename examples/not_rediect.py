#!/usr/bin/env python3

from asynclient import ac

@ac.coro
def get(url):
    resp = yield from ac.get(url, follow_redirects=False)
    print(resp.body)

ac.run(get("google.com"))
