#!/usr/bin/env python3

import asynclient as ac

@ac.coro
def get(*urls):
    futures = []
    for url in urls:
        # use ``ac.async`` instead of ``yield from``
        # tasks will run in parallel
        fu = ac.async(ac.fetch(url))
        futures.append(fu)

    resps = yield from ac.gather(*futures)

    for resp in resps:
        print(resp.body)

ac.run(get("google.com", "http://www.reddit.com/"))
