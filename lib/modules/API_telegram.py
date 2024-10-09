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
import requests
import html
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
import schedule

# -*-*-*-*-*-*-*-*-*-*-* #
#     Project Modules    #
# -*-*-*-*-*-*-*-*-*-*-* #
# framework
from lib.framework.markI import MkI
from lib.modules.API_google import GoogleSheetsAPI



class TelegramAPI():
    def __init__(
            self,
            mk1               : MkI,
            enable_polling    : bool,
            google_sheets_api : GoogleSheetsAPI
        ) :
        ## System Design
        self.mk1 = mk1

        ## __________ *** Initializing (other services) *** __________
        self.google_sheets_api = google_sheets_api

        ## __________ *** Initializing (attributes) *** _______
        self.token_key = str(self.mk1.config.get("api_telegram","token_key"))

        ## __________ *** Initializing (client) *** __________
        self.service    = self.build_client()
        self.updater    = self.build_updater()
        self.dispatcher = self.build_dispatcher()

        ## __________ *** Initializing (registration, polling) *** __________
        self.register_commands()
        self.start_polling(enable_polling)


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

    def start_polling(self, enable_polling : bool ):
        if enable_polling : 
            self.updater.start_polling()



    def start_command(
            self, 
            update   : telegram.Update, 
            context : telegram.ext.CallbackContext
        ) -> None:
        """ Command to start the bot.

            :param update: The update object containing message details.
            :param context: The context object containing additional data.
        """

        update.message.reply_text("Hi! I will send you the daily Gmail news report every morning.")


    def register_chat_id_command(
            self, 
            update  : Update, 
            context : CallbackContext
        ) -> None:

        chat_id = str(update.message.chat_id)
        sheets_reporter_id                  = str(self.mk1.config.get("google_sheets","reporter_id"))
        sheets_reporter_tab_config_telegram = str(self.mk1.config.get("google_sheets","reporter_tab_config_telegram"))

        chat_ids = self.google_sheets_api.get_df_from_tab(
            spreadsheet_id          = sheets_reporter_id,
            spreadsheet_range_name  = sheets_reporter_tab_config_telegram,
            spreadsheet_has_index   = False
        )

        if not chat_id in chat_ids['chat_ids'].values:
            self.google_sheets_api.append_rows_to_tab(
                df                      = pd.DataFrame([chat_id]),
                spreadsheet_id          = sheets_reporter_id,
                spreadsheet_range_name  = sheets_reporter_tab_config_telegram,
                spreadsheet_has_index   = False,
                spreadsheet_has_headers = False
            )
            update.message.reply_text(f'Your chat ID is {chat_id} and has been registered for the Daily Newsletter Reporter\n𝐍𝐨. 𝐨𝐟 𝐫𝐞𝐠𝐢𝐬𝐭𝐞𝐫𝐞𝐝 𝐮𝐬𝐞𝐫𝐬 = {chat_ids.shape[0] + 1}')
        else : 
            update.message.reply_text(f'Your chat ID is {chat_id} is already registered!\n𝐍𝐨. 𝐨𝐟 𝐫𝐞𝐠𝐢𝐬𝐭𝐞𝐫𝐞𝐝 𝐮𝐬𝐞𝐫𝐬 = {chat_ids.shape[0]}')


    def unregister_chat_id_command(
            self, 
            update  : Update, 
            context : CallbackContext
        ) -> None:

        chat_id = str(update.message.chat_id)
        sheets_reporter_id                  = str(self.mk1.config.get("google_sheets","reporter_id"))
        sheets_reporter_tab_config_telegram = str(self.mk1.config.get("google_sheets","reporter_tab_config_telegram"))

        # Fetch the current chat IDs from the Google Sheets tab
        chat_ids = self.google_sheets_api.get_df_from_tab(
            spreadsheet_id          = sheets_reporter_id,
            spreadsheet_range_name  = sheets_reporter_tab_config_telegram,
            spreadsheet_has_index   = False
        )

        # Check if the chat ID exists in the Google Sheets tab
        if chat_id in chat_ids['chat_ids'].values:
            # Remove the chat ID
            updated_chat_ids = chat_ids[chat_ids['chat_ids'] != chat_id]

            # Update the Google Sheets tab by overwriting with the updated DataFrame
            self.google_sheets_api.write_df_to_tab(
                df                      = updated_chat_ids,
                spreadsheet_id          = sheets_reporter_id,
                spreadsheet_range_name  = sheets_reporter_tab_config_telegram,
                spreadsheet_has_index   = False,
                spreadsheet_has_headers = True,  # Assuming the sheet has headers]
                clear_before_write      = True
            )
            update.message.reply_text(f'Your chat ID {chat_id} has been unregistered from the Daily Newsletter Reporter. \n 𝐍𝐨. 𝐨𝐟 𝐫𝐞𝐠𝐢𝐬𝐭𝐞𝐫𝐞𝐝 𝐮𝐬𝐞𝐫𝐬 = {updated_chat_ids.shape[0]}')
        else:
            update.message.reply_text(f'Your chat ID {chat_id} was not found in the registered list.\n𝐍𝐨. 𝐨𝐟 𝐫𝐞𝐠𝐢𝐬𝐭𝐞𝐫𝐞𝐝 𝐮𝐬𝐞𝐫𝐬 = {chat_ids.shape[0]}')





    def get_latest_report_command(
            self, 
            update  : Update, 
            context : CallbackContext
        ):

        with open(file_path, 'r') as json_file:
            data = json.load(json_file)  # Parse the JSON file
            return data


        chat_id = update.message.chat_id 
        pass



    def help_command(
            self, 
            update: Update, 
            context: CallbackContext
        ) -> None:
        """ Command to provide information on available commands."""
        help_text = (
            "Here are the commands you can use:\n\n"
            "/start - Start the bot and receive daily updates.\n"
            "/register_chat_id - Register your chat ID.\n"
            "/unregister_chat_id - Unregister your chat ID.\n"
            "/get_latest_report - Get most recent newsletter daily report.\n"
            "/help - Get a list of available commands."
        )
        update.message.reply_text(help_text)


    

    def register_commands(self) -> None:
        """ Register command handlers for the bot. """
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("register_chat_id", self.register_chat_id_command))
        self.dispatcher.add_handler(CommandHandler("unregister_chat_id", self.unregister_chat_id_command))
        self.dispatcher.add_handler(CommandHandler("get_latest_report", self.get_latest_report_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))

    # ________________________________________________________________________________________________ #

    def collect_chat_ids(self) -> set:
        """ Collects chat IDs from the bot's existing updates without re-initializing the bot.
        
            :return: A set of unique chat IDs.
        """
        try:
            # Fetch the updates from the bot using the pre-initialized service (self.service)
            updates = self.service.get_updates()  # Use the service bot instance to get updates
            chat_ids = set()

            # Loop through the updates and extract chat IDs
            for update in updates:
                if update.message:  # Check if there's a message in the update
                    chat_id = update.message.chat.id
                    chat_ids.add(chat_id)

            self.mk1.logging.logger.info(f"Collected {len(chat_ids)} chat IDs.")
            return chat_ids
        
        except Exception as e:
            self.mk1.logging.logger.error(f"(TelegramAPI.collect_chat_ids) Failed to collect chat IDs: {e}")
            return set()


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

    def set_data(
            self, 
            summary_per_category : pd.DataFrame, 
            today                : dt.datetime, 
            chat_ids             : pd.DataFrame, 
        ) -> None:
        """ Set data for sending news reports.

            :param summary_per_category: DataFrame containing the summary per category.
            :param today: The current date and time.
            :param chat_ids: The list of chat IDs to which messages will be sent.
        """
        self.summary_per_category = summary_per_category
        self.today = today
        self.chat_ids = chat_ids['chat_ids'].astype(str).tolist()
    

    def send_news_report(self, context: telegram.ext.CallbackContext = None) -> None:
        """
        Send the news report to Telegram.

        :param context: The context object containing additional data.
        """
    
        # Introductory message
        today = dt.datetime.now()

        for chat_id in self.chat_ids : 
            self.service.send_message(
                chat_id = chat_id,
                text    = f"📰 𝐃𝐀𝐈𝐋𝐘 𝐍𝐄𝐖𝐒 𝐑𝐄𝐏𝐎𝐑𝐓 - {today.strftime('%Y.%m.%d')} 🗓️"
            )

        # Newsletters summaries
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
        schedule.every().day.at(day_at).do(
            self.send_news_report, 
            None
        )  # Schedule for 1 minute later

        while True:
            schedule.run_pending()
            jobs = schedule.get_jobs()
            if jobs and jobs[0].last_run:
                self.mk1.logging.logger.info(f"(TelegramAPI.run_daily_news_report) Last run time: {jobs[0].last_run}")
                break
            time.sleep(10)
        

