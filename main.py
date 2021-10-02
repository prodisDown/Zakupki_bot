#!/bin/python3

import sys, os, copy, re, time, math
from multiprocessing import Pipe
import json

from src.MyBot import MyBot
from src.MyFeeder import MyFeeder
from src.Common import Chat, Subscription, updatePush


bot_config = {
    'token': '',
    'usage_message': 'Это бот уведомлений об изменениях '+\
    'на электронных торговых площадках. '+\
    'Он проверяет последние обновления на сайте и присылает сообщения об изменениях '+\
    'в соответсвии с вашими подписками.\n\n'+\
    ' /create <url> — создать подписку на указанный URL, чтобы получать обновления.\n'+\
    ' /delete <id> — отписаться от указанного обновления. ID подписки '+\
    'можно узнать из уведомлений об обновлении.',

    'answer_ErrorUrlIsNotPresent': 'Укажите URL, на который хотите подписаться.',
    'answer_ErrorUrlIsNotInList': 'Данный URL не поддерживается ботом.',
    'answer_ErrorMaximumSubs': 'Достигнут разрешенный максимум подписок. Удалите лишние чтобы добавить новые.',
    'answer_ErrorSubNotHere': 'Подписка с таким ID отсутствует.',

    'answer_SubCreated': 'Подписка создана.',
    'answer_SubDeleted': 'Подписка удалена.',
}


chats: dict = {} # [int, Chat]  # keys are telegram chat ID's


if __name__ == '__main__':

## Preparations

    # Read secret token from the file
    with open('private.key', 'r') as key_file:
        bot_config['token'] = (key_file.readline())[:-1]

    # Duplex pipe, one end to bot, the other to feeder
    pipe_botEnd, pipe_feederEnd = Pipe(duplex=True)

## Start bot and feeder
    bot = MyBot(bot_config, chats, pipe_botEnd)
    feeder = MyFeeder(chats, pipe_feederEnd)

    while True:
        pass
