#!/usr/bin/env python3

import asynclient as ac

@ac.coro
def get(url):
    try:
        resp = yield from ac.fetch(url, timeout=0)
        print(resp.body)
    except ac.Timeout as e:
        print("connection timeout")

ac.run(get("google.com"))
