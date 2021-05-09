import asyncio
import time
import threading


def my_sync_fun():
    print(f'my_sync_fun start: {threading.get_ident()}')
    time.sleep(5)
    print(f'my_sync_fun stop {threading.get_ident()}')


async def updater():
    counter = 0
    print(f'updater start {threading.get_ident()}!')
    asyncio.get_event_loop().run_in_executor(None, my_sync_fun)
    for i in range(20):
        print(f'updater {counter} - {threading.get_ident()}!')
        counter = counter + 1
        await asyncio.sleep(0.5)
    print(f'updater stop! {threading.get_ident()}')


asyncio.run(updater())
