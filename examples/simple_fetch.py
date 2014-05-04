#!/usr/bin/env python3

import asynclient as ac

@ac.coro
def get(url):
    # waiting for ``ac.fetch``
    resp = yield from ac.fetch(url)
    print(resp.body)

ac.run(get("google.com"))
