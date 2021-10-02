import sys, os, json, re, time, math
from copy import deepcopy

from multiprocessing import Pipe
from threading import Lock


class Subscription:

    def __init__(self, sub_id: int, url: str):
        self.sub_id = deepcopy(sub_id); del sub_id
        self.url = deepcopy(url); del url

        self.DEFAULT_nextUpdate_delay = 60  # Seconds

        self._lock = Lock()

        self.data: str = None   # This needs to be printable
        self._data_custom = None    # Opaque parser data storage
        self.dataTime = 0       # POSIX's epoch
        self.nextUpdate = 0     # POSIX's epoch


    def isUpdateNeeded(self):
        if math.floor(time.time()) >= self.nextUpdate:
            return True
        else:
            return False

    def putNoUpdate(self, nextUpdate: int = None, delay: int = None):
        if nextUpdate == None:
            if delay == None:
                nextUpdate = math.floor(time.time()) + self.DEFAULT_nextUpdate_delay
            else:
                nextUpdate = math.floor(time.time()) + delay
        self.nextUpdate = deepcopy(nextUpdate)

    def putData(self,
        data: str = None,
        dataTime: int = None,
        nextUpdate: int = None
    ):
        if dataTime == None:
            dataTime = math.floor(time.time())
        if nextUpdate == None:
            nextUpdate = dataTime + self.DEFAULT_nextUpdate_delay
        self.data = deepcopy(data)
        self.dataTime = deepcopy(dataTime)
        self.nextUpdate = deepcopy(nextUpdate)


class Chat:

    def __init__(self, chat_id):
        self.chat_id = deepcopy(chat_id); del chat_id
        self.subs: dict = {} # [int, Subscription]
        self.last_sub_id: int = None
        self.lastReport = 0     # POSIX's epoch

    def createSub(self, sub_url):
        MAXIMUM_SUBS = 500
        MIN_SUB_ID = 1          # sub_id can't be 0
        if self.last_sub_id == None:
            new_sub_id = MIN_SUB_ID
        else:
            new_sub_id = (self.last_sub_id + 1)%(MAXIMUM_SUBS+MIN_SUB_ID)
        while new_sub_id != self.last_sub_id:
            if new_sub_id in self.subs:
                new_sub_id = (new_sub_id + 1)%(MAXIMUM_SUBS+MIN_SUB_ID)
                continue
            self.subs[new_sub_id] = Subscription(new_sub_id, sub_url)
            self.last_sub_id = new_sub_id
            return self.subs[new_sub_id]
        else:
            # If there is more then MAXIMUM_SUBS subs, do nothing
            return None

    def deleteSub(self,sub_id):
        if sub_id not in self.subs:
            return False
        with self.subs[sub_id]._lock:
            del self.subs[sub_id]
        return True


def updatePush(pipe: Pipe,
        chat_id: int,
        sub_id: int,
        timestamp: int = None,
):
    if timestamp == None:
        timestamp = math.floor(time.time())
    # By design, if you push (-1 * chat_id) or (-1 * sub_id), it means that corresponding object needs to be deleted or not accessible anymore.
    pipe.send((chat_id,sub_id,timestamp))


def sanitizeURL(url: str):
    import urllib.parse as ulP

    return ulP.urlunsplit(ulP.urlsplit(url))


def onlyPageURL(url: str):
    import urllib.parse as ulP

    p0 = ulP.urlsplit(url)
    p1 = p0._replace(**{'query':'','fragment':''})

    return ulP.urlunsplit(p1)
