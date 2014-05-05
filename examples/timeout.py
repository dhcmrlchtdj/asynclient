#!/usr/bin/env python3

from asynclient import ac

@ac.coro
def get(url):
    try:
        resp = yield from ac.get(url, timeout=0)
        print(resp.body)
    except TimeoutError as e:
        print("connection timeout")

ac.run(get("google.com"))
