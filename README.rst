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
