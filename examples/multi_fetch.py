#!/usr/bin/env python3

from asynclient import ac

@ac.coro
def get(*urls):
    futures = []
    for url in urls:
        # ``async`` convert ``coroutine`` to ``task``
        # ``event loop`` will schedule ``task``
        fu = ac.async(ac.get(url))
        futures.append(fu)

    resps = yield from ac.gather(*futures)

    for resp in resps:
        print(resp.body)

ac.run(get("google.com", "http://www.reddit.com/"))
