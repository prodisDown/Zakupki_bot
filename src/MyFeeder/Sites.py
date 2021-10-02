import sys, os, json, re, time, math
from copy import deepcopy

from ..Common import Chat, Subscription, updatePush
from ..Common import sanitizeURL, onlyPageURL

import urllib.parse

import urllib.request
from bs4 import BeautifulSoup


### List of supported URLs.

SUPPORTED_SITES = [
    'https://www.roseltorg.ru/procedures/search',
#    'https://zakupki.gov.ru/epz/order/extendedsearch/results.html',
]


### List of methods, different for each URL.
#   Returns True if any update, False if not.
#   my_sub is already locked and accessible only by this methods when they called.

SITES_METHODS = []

#0
def _roseltorg_sm(my_sub: Subscription) -> bool:

    class Data_Custom:
        def __init__(self):
            self.top_lotPath: str = None

    prev_state: Data_Custom = my_sub._data_custom
    this_state: Data_Custom = Data_Custom()

    # Construct URL
    my_url = 'https://www.roseltorg.ru/procedures/search_ajax'
    IGNORED_QC = set(['page','from',])
    user_query: dict = urllib.parse.parse_qs(urllib.parse.urlsplit(my_sub.url).query)
    for p in IGNORED_QC:
        if p in user_query:
            del user_query[p]
    my_query: str = urllib.parse.urlencode(user_query, doseq=True)

    # Get the page as str. If any error, return False.
    try:
        resp = urllib.request.urlopen(my_url + '?' + my_query)
    except HTTPError as ex:
        print('method:',
                'code:',ex.code,
                ' reason:',ex.reason,
                flush=True
            )
        return False
    except URLError as ex:
        print('method:',ex.reason, flush=True)
        return False
    except:
        return False

    if resp.status != 200:
        print('method:','response:',resp.status,', resp.status != 200',flush=True)
        return False

    try:
        page = resp.read().decode()
    except:
        return False

    # Get first lot link
    soup = BeautifulSoup(page, 'html.parser')
    lotLinks = []
    try:
        for item in soup.find_all('div', attrs={'class': 'search-results__item'}):
            info = item.find('div', attrs={'class': 'search-results__info'})
            header = info.find('div', attrs={'class': 'search-results__header'})
            lot = header.find('div', attrs={'class': 'search-results__lot'})
            lotLinks.append(lot.a.get('href'))
    except:
        return False

    # Compare new top link with old one
    if len(lotLinks) < 1:
        return False
    this_state.top_lotPath = lotLinks[0]

    def _prepareReturnTrue():
        my_sub._data_custom = deepcopy(this_state)   # Save this state in my_sub
        site_url = 'https://www.roseltorg.ru'
        my_sub.putData('Одно или более изменений. Последний лот:\n  ' +\
                site_url + this_state.top_lotPath
        )
        print('method:','Update!',time.time(), flush=True)

    if prev_state is None:
        _prepareReturnTrue(); return True
    if prev_state.top_lotPath != this_state.top_lotPath:
        _prepareReturnTrue(); return True

    # If all is good but there is no updates yet
    my_sub.putNoUpdate(delay=60,)
    return False

SITES_METHODS.append(_roseltorg_sm)

#1
def _zakupkigovru_sm(my_sub: Subscription) -> bool:
    return False

SITES_METHODS.append(_zakupkigovru_sm)


### Construct a dict of methods.
SITES_DICT = dict(zip(SUPPORTED_SITES, SITES_METHODS))
