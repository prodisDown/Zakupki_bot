import sys, os, json, re, time, math
from copy import deepcopy

from multiprocessing import Pipe

import telegram
from telegram.ext import Updater, CommandHandler, Filters
import urllib.parse

from ..Common import Chat, Subscription, updatePush
from ..Common import sanitizeURL, onlyPageURL
from ..MyFeeder.Sites import SUPPORTED_SITES


class MyBot:

    def _return_chat(self, chat_id: int):
        if chat_id not in self.chats:
            self.chats[chat_id] = Chat(chat_id)
        return self.chats[chat_id]

    def _answer_on_command(self, update, context, text_to_send: str):
        context.bot.send_message(
            update.effective_chat.id,
            text_to_send
        )

    def __init__(self,
        config,
        chats: dict, # [int, Chat]
        pipe: Pipe, # duplex
    ):
        self.config = deepcopy(config); del config
        self.chats = chats
        self.pipe = pipe

        self.updater = Updater(token=self.config['token'])

    ## Handlers and callbacks
        handlers = []

    # '/start' handler
        def _comm_start(update,context):
            context.bot.send_message(
                update.effective_chat.id,
                self.config['usage_message']
            )
        handlers.append(CommandHandler('start', _comm_start, ~Filters.update.edited_message))

    # '/create' handler
        def _comm_create(update,context):
            my_chat = self._return_chat(update.effective_chat.id)
            acceptable_urls = '\nСписок текущих поддерживаемых URL:\n' + '\n'.join([f' {w}' for w in SUPPORTED_SITES])

            if len(context.args) < 1:
                self._answer_on_command(update, context,
                    self.config['answer_ErrorUrlIsNotPresent'] + acceptable_urls,
                )
                return

            url_arg = sanitizeURL(context.args[0])
            tmp_url = onlyPageURL(url_arg)

            if tmp_url not in SUPPORTED_SITES:
                self._answer_on_command(update, context,
                    self.config['answer_ErrorUrlIsNotInList'] + acceptable_urls
                )
                return

            new_sub = my_chat.createSub(url_arg)

            if new_sub == None:
                context.bot.send_message(
                    update.effective_chat.id,
                    self.config['answer_ErrorMaximumSubs']
                )
                return

            updatePush(pipe,
                update.effective_chat.id,
                new_sub.sub_id
            )

            self._answer_on_command(update, context,
                self.config['answer_SubCreated'] + ' ID: ' + str(new_sub.sub_id)
            )
            return

        handlers.append(CommandHandler('create', _comm_create, ~Filters.update.edited_message))

    # '/delete' handler
        def _comm_delete(update,context):
            my_chat = self._return_chat(update.effective_chat.id)

            if len(context.args) < 1:
                self._answer_on_command(update, context,
                    self.config['answer_ErrorSubNotHere']
                )
                return

            try:
                sub_arg = int(context.args[0], 10)
            except:
                self._answer_on_command(update, context,
                    self.config['answer_ErrorSubNotHere']
                )
                return

            if sub_arg not in my_chat.subs:
                self._answer_on_command(update, context,
                    self.config['answer_ErrorSubNotHere']
                )
            else:
                c_sub = my_chat.subs[sub_arg]

                c_sub._lock.acquire()       # It will be deleted, no need to release
                my_chat.deleteSub(sub_arg)
                self._answer_on_command(update, context,
                    self.config['answer_SubDeleted']
                )
            return

        handlers.append(CommandHandler('delete', _comm_delete, ~Filters.update.edited_message))

    ## Register all handlers
        for x in handlers:
            self.updater.dispatcher.add_handler(x)

    ## END Handlers and callbacks

    ## Report updates
        def _update_reporter_loop(context):
            while self.pipe.poll(None):     # Infinite loop
                (chat_id, sub_id, timestamp) = self.pipe.recv()
                print('bot:','update:',(chat_id,sub_id,timestamp), time.time(), flush=True)

                # Skip negative values of chat_id & sub_id
                if (chat_id < 0) or (sub_id < 0):
                    continue

                # Check if chat and sub still exists
                if chat_id not in self.chats:
                    continue
                if sub_id not in self.chats[chat_id].subs:
                    continue
                c_sub = self.chats[chat_id].subs[sub_id]

                if not c_sub._lock.acquire(timeout=30):
                    print('bot:','update:','lock timeout', time.time(), flush=True)
                    continue

                # Check if message is not outdated
                if timestamp < c_sub.dataTime:
                    c_sub._lock.release()
                    continue
                text_to_send = 'ID ' + str(sub_id) + '\n' +\
                        c_sub.url + '\n\n' + c_sub.data;
                self.chats[chat_id].lastReport = math.floor(time.time())
                context.bot.send_message(
                    chat_id, text_to_send
                )

                c_sub._lock.release()

        print('bot:','run tasks',time.time(), flush=True)

        self.updater.job_queue.run_once(_update_reporter_loop, 0)

    ### Bot starts to handle chats
        print('bot:','handling messages from Telegram',time.time(), flush=True)
        self.updater.start_polling()
