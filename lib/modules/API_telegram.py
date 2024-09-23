# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    [*] Description : Py3 class for MarkI system design for all frameworks
    [*] Author      : dgeorgiou3@gmail.com
    [*] Date        : Jan, 2024
    [*] Links       :
"""

# -*-*-*-*-*-*-*-*-*-*-* #
#     Basic Modules      #
# -*-*-*-*-*-*-*-*-*-*-* #
import os, json, re, time
import numpy    as np
import pandas   as pd
import datetime as dt
from retry                  import retry
from tqdm                   import tqdm
from datetime               import datetime
from urllib.parse           import unquote
from typing                 import Dict, Any, List, Tuple
from concurrent.futures     import ThreadPoolExecutor

# -*-*-*-*-*-*-*-*-*-*-* #
#   Third-Party Modules  #
# -*-*-*-*-*-*-*-*-*-*-* #
import telegram
import html
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
import schedule



class TelegramAPI():
    def __init__(
            self,
            mk1
        ) :
        ## System Design
        self.mk1 = mk1

        ## __________ *** Initializing (attributes) *** _______
        self.token_key = str(self.mk1.config.get("api_telegram","token_key"))
        ## __________ *** Initializing (client) *** __________
        self.service    = self.build_client()
        self.updater    = self.build_updater()
        self.dispatcher = self.build_dispatcher()

        ## __________ *** Initializing (registration, polling) *** __________
        self.register_commands()
        #self.start_polling() # Check ChatGPT (maybe using flask with the bot)


    # Service
    def build_client(self):
        try:
            # Creating the OpenAI API client
            service = telegram.Bot(
                token = self.token_key
            )

            self.mk1.logging.logger.info("(TelegramAPI.build_client) Service build succeeded")
            return service

        except Exception as e:
            self.mk1.logging.logger.error(f"(TelegramAPI.build_client) Service build failed: {e}")
            raise e
            return None

    def build_updater(self):
        try:
            # Creating the OpenAI API client
            updater = Updater(
                self.token_key, 
                use_context = True
            )

            self.mk1.logging.logger.info("(TelegramAPI.build_updater) Updated build succeeded")
            return updater

        except Exception as e:
            self.mk1.logging.logger.error(f"(TelegramAPI.build_updater) Updated build failed: {e}")
            raise e

    def build_dispatcher(self):
        return self.updater.dispatcher

    def start_polling(self):
        self.updater.start_polling()



    def start_command(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        Command to start the bot.

        :param update: The update object containing message details.
        :param context: The context object containing additional data.
        """
        update.message.reply_text("Hi! I will send you the daily Gmail news report every morning.")


    def get_chat_id_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.message.chat_id
        update.message.reply_text(f'Your chat ID is {chat_id}')


    def help_command(self, update: Update, context: CallbackContext) -> None:
        """
        Command to provide information on available commands.
        """
        help_text = (
            "Here are the commands you can use:\n\n"
            "/start - Start the bot and receive daily updates.\n"
            "/getchatid - Get your chat ID.\n"
            "/help - Get a list of available commands."
        )
        update.message.reply_text(help_text)


    def register_commands(self) -> None:
        """ Register command handlers for the bot. """
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("getchatid", self.get_chat_id_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))

    # ________________________________________________________________________________________________ #

    def escape_markdown(self, text):
        # Escape only markdown-sensitive characters used by Telegram
        # We escape: '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.'
        # Period (.) only needs escaping if it's part of a markdown entity, so we avoid over-escaping it
        markdown_chars = r'_*\[\]()~`>#+-=|{}'

        # Escape only the necessary markdown characters
        escaped_text = re.sub(r'([{}])'.format(re.escape(markdown_chars)), r'\\\1', text)
        
        return escaped_text


    def fix_common_entities(self, text):
        # Replace common problematic characters with their HTML entity equivalents
        text = html.escape(text, quote=False)  # Escape <, >, and & only
        return text

    def split_text(self, text, limit = 4000, max_messages=30):
        """ Telegram limit is 4096 characters. further more, I shouldn't send more than 30 messages, othwerwise it leads to timeout """
        # Escape markdown-sensitive characters
        text = self.fix_common_entities(text)

        # Split the text into chunks of 'limit' size while not exceeding 'max_messages'
        chunks = []
        
        # If the text is smaller than the limit, just return it
        if len(text) <= limit:
            return [text]
        
        # Splitting the text into chunks with a maximum size of 'limit'
        for i in range(0, len(text), limit):
            chunks.append(text[i:i+limit])
            
            # Break if the number of chunks exceeds the max_messages constraint
            if len(chunks) >= max_messages:
                break
        
        return chunks


    def set_data(self, summary_per_category: pd.DataFrame, today: dt.datetime, chat_ids: List[str]) -> None:
        """
        Set data for sending news reports.

        :param summary_per_category: DataFrame containing the summary per category.
        :param today: The current date and time.
        :param chat_ids: The list of chat IDs to which messages will be sent.
        """
        self.summary_per_category = summary_per_category
        self.today = today
        self.chat_ids = chat_ids

    

    def send_news_report(self, context: telegram.ext.CallbackContext = None) -> None:
        """
        Send the news report to Telegram.

        :param context: The context object containing additional data.
        """
        messages = []
        for key, values in self.summary_per_category.items():
            d = self.today.strftime('%Y.%m.%d')
            message = f"{key} ({d})\n\n"
            if len(values) > 0:
                for text in values:
                    message += f"{text}\n\n"

            message_chunks = self.split_text(message)
             
            for chat_id in self.chat_ids : 
                for message in message_chunks :
                    self.service.send_message(
                        chat_id    = chat_id,
                        text       = message,
                        #parse_mode = "Markdown"
                    )

    def run_daily_news_report(self) -> None:
        """ Schedule and run the daily news report."""
        day_at = (dt.datetime.now() + dt.timedelta(minutes = 1)).strftime("%H:%M")
        schedule.every().day.at(day_at).do(self.send_news_report, None)  # Schedule for 1 minute later

        while True:
            schedule.run_pending()
            jobs = schedule.get_jobs()
            if jobs and jobs[0].last_run:
                self.mk1.logging.logger.info(f"(TelegramAPI.run_daily_news_report) Last run time: {jobs[0].last_run}")
                break
            time.sleep(10)
        

