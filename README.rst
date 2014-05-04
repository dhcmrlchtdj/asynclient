asynclient
==========

An asynchronous http client.



Basic Usage
-----------

.. code:: python

    import asynclient as ac

    @ac.coro
    def get():
        resp = yield from ac.fetch("google.com")
        print(resp.body)

    ac.run(get())



.. code:: python

    import asynclient as ac

    @ac.coro
    def get(*urls):
        fs = []
        for url in urls:
            f = ac.async(ac.fetch(url))
            fs.append(f)
        ret = yield from ac.gather(*fs)
        print(ret)

    ac.run(get("google.com", "baidu.com"))
