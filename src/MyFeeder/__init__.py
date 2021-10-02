import sys, os, json, re, time, math
from copy import deepcopy

from multiprocessing import Pipe
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor

import urllib.parse

from ..Common import Chat, Subscription, updatePush
from ..Common import sanitizeURL, onlyPageURL
from .Sites import SUPPORTED_SITES, SITES_DICT


class MyFeeder:

    def _main_loop(self):

        update_list: dict = {} # [int, set[int]]

        subWorkers = ThreadPoolExecutor(max_workers=3)
        subWorkers_tasks: dict = {} # [tuple[int,int], object]


        def _my_sub_worker(self,
            my_chat_id: int,
            my_sub: Subscription
        ):
            url_path = onlyPageURL(my_sub.url)
            url_method = SITES_DICT[url_path]
            #print('worker:',url_path,url_method, flush=True)
            with my_sub._lock:
                updated: bool = url_method(my_sub)
                if updated:
                    print('worker:',(my_chat_id,my_sub.sub_id),'pushing update', time.time(), flush=True)
                    updatePush(self.pipe, my_chat_id, my_sub.sub_id)
            return


        def _read_pipe_and_update_list(self):
            (chat_id, sub_id, timestamp) = self.pipe.recv()
            print('read:','update:', chat_id, sub_id, timestamp, flush=True)

            # Delete chat and/or sub from update_list if its ID is negative
            if (chat_id < 0) and (abs(chat_id) in update_list):
                del update_list[abs(chat_id)]
                return
            if chat_id == 0:
                return

            if (sub_id < 0) and (abs(sub_id) in update_list[chat_id]):
                update_list[chat_id].discard(abs(sub_id))
                return
            if sub_id == 0:
                return

            # Add chat and/or sub to update_list
            if chat_id not in update_list:
                update_list[chat_id] = set()
            update_list[chat_id].add(sub_id)
            return


        def _keep_tasks_busy(self):
            for my_chat_id in update_list:
                if my_chat_id not in self.chats:
                    print('busy:',my_chat_id,'chat is already deleted', flush=True)
                    continue
                for my_sub_id in update_list[my_chat_id]:
                    if my_sub_id not in self.chats[my_chat_id].subs:
                        print('busy:',my_chat_id,my_sub_id,'sub is already deleted', flush=True)
                        continue
                    t = (my_chat_id,my_sub_id,)
                    if t in subWorkers_tasks:
                        if not subWorkers_tasks[t].done:
                            print('busy:',t,'not ready', flush=True)
                            continue

                    my_sub = self.chats[my_chat_id].subs[my_sub_id]
                    if not my_sub.isUpdateNeeded():
                        continue
                    #print('busy:','submit:', my_chat_id, my_sub_id, time.time(), flush=True)
                    subWorkers_tasks[t] = subWorkers.submit(
                            _my_sub_worker,
                            self, my_chat_id, my_sub
                        )
            return

        ## Infinite loop
        while True:
            ## Receive changes in chats
            while self.pipe.poll(5):
                _read_pipe_and_update_list(self)

            ## Iterate through subs and do stuff
            _keep_tasks_busy(self)


    def __init__(self,
        chats: dict, # [int, Chat]
        pipe: Pipe # duplex
    ):
        self.chats = chats
        self.pipe = pipe

        self.loop = Thread(target=self._main_loop, name="feeder_loop")
        self.loop.start()

