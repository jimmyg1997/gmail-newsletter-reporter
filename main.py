#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    [*] Description : Gmail Reporter
    [*] Author      : dgeorgiou3@gmail.com
    [*] Date        :
    [*] Links       :
"""
# -*-*-*-*-*-*-*-*-*-*-* #
#     Basic Modules      #
# -*-*-*-*-*-*-*-*-*-*-* #
import os, json, time, glob,argparse, re
import numpy     as np
import functools as ft
import pandas    as pd
import datetime  as dt
import openai
import tiktoken
import langid
from openai          import OpenAI
from urllib.parse    import unquote
from bs4             import BeautifulSoup
from tqdm            import tqdm
from typing          import Dict, Any, List
from IPython.display import display
from concurrent.futures import ThreadPoolExecutor

# -*-*-*-*-*-*-*-*-*-*-* #
#     Project Modules    #
# -*-*-*-*-*-*-*-*-*-*-* #
# framework
from lib.framework.markI import *

# handlers
from lib.handlers.data_handling   import DataLoader
from lib.handlers.email_analyzing import EmailAnalyzer
from lib.handlers.reporting import Reporter

# modules
from lib.modules.API_openai import OpenaiAPI
from lib.modules.API_telegram import TelegramAPI
from lib.modules.API_google import (
    GoogleAPI, GoogleSheetsAPI, GoogleEmailAPI, GoogleDocsAPI, GoogleDriveAPI
)

# helpers
import lib.helpers.utils as utils


class Controller():
    def __init__(self, mk1 : MkI) :
        self.mk1  = mk1
        self.args = self.parsing()

        self.__null_values = [
            None, np.nan, "", "#N/A", "null", "nan", "NaN"
        ]


    def parsing(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--operation",
            "-o",
            type    = str,
            default = "get_email_report" ,
            help    = "Options = {get_email_report}"
        )

        parser.add_argument(
            "--days_diff",
            "-dd",
            type    = int,
            default = 0,
            help    = "Options = {..,-2,-1,0, 1, 2,...}"
        )

        parser.add_argument(
            "--schedule_hour",
            "-sh",
            type    = int,
            default = 7,
            help    = "Options (0,23) in UTC time"
        )

        parser.add_argument(
            "--hours",
            "-ho",
            type    = int,
            default = 24,
            help    = "Options = {0, 1, ...}"
        )
        parser.add_argument(
            "--enable_polling",
            "-poll",
            action = 'store_true',
            help    = "Options = {True, False}"
        )
        return parser.parse_args()



    def run_initialization(self, enable_telegram : bool):
        # Initializing Modules
        self.openai_api = OpenaiAPI(
            mk1 = self.mk1
        )
        self.google_api = GoogleAPI(
            mk1 = self.mk1
        )
        self.google_sheets_api = GoogleSheetsAPI(
            mk1        = self.mk1,
            google_api = self.google_api
        )
        self.google_email_api  = GoogleEmailAPI(
            mk1        = self.mk1,
            google_api = self.google_api
        )
        self.google_drive_api  = GoogleDriveAPI(
            mk1        = self.mk1,
            google_api = self.google_api
        )
        self.google_docs_api = GoogleDocsAPI(
            mk1        = self.mk1,
            google_api = self.google_api
        )

        if enable_telegram : 
            self.telegram_api = TelegramAPI(
                mk1 = self.mk1,
                enable_polling = self.args.enable_polling,
                google_sheets_api = self.google_sheets_api
            )
        
        # Initializing Handlers
        self.data_loader = DataLoader(
            mk1               = self.mk1,
            google_sheets_api = self.google_sheets_api
        )
        self.email_analyzer = EmailAnalyzer(
            mk1              = self.mk1,
            google_email_api = self.google_email_api,
            openai_api       = self.openai_api
        )
        self.reporter = Reporter(
            mk1               = self.mk1,
            google_sheets_api = self.google_sheets_api,
            google_drive_api  = self.google_drive_api,
            google_docs_api   = self.google_docs_api
        )


    def _refresh_session(self):
        self.run_initialization()


    def run_get_email_report(self):
        tqdm.pandas()

        ## _______________ *** Configuration (attributes) *** _______________ #
        # Google Sheets
        sheets_reporter_id                     = str(self.mk1.config.get("google_sheets","reporter_id"))
        sheets_reporter_tab_config_newsletters = str(self.mk1.config.get("google_sheets","reporter_tab_config_newsletters"))
        sheets_reporter_tab_config_docs        = str(self.mk1.config.get("google_sheets","reporter_tab_config_docs"))
        sheets_reporter_tab_config_docs_ids    = str(self.mk1.config.get("google_sheets","reporter_tab_config_docs_ids"))
        sheets_reporter_tab_config_telegram    = str(self.mk1.config.get("google_sheets","reporter_tab_config_telegram"))
        sheets_reporter_tab_logs               = str(self.mk1.config.get("google_sheets","reporter_tab_logs"))

        # App storage
        fn_path_summary_txt  = str(self.mk1.config.get("app_storage","fn_path_summary_txt"))
        fn_path_summary_json = str(self.mk1.config.get("app_storage","fn_path_summary_json"))

        # Attributes
        hours = self.args.hours
        days  = self.args.days_diff
        today = datetime.now() + dt.timedelta(days = days)
        fn_path_summary_txt = fn_path_summary_txt.format(day = today.strftime('%Y%m%d'))
        fn_path_summary_json = fn_path_summary_json.format(day = today.strftime('%Y%m%d'))

        ## _____________________________________________________________________________________________________________________ ##
        """
            1. (DataFrame Operations) Initialize logs dictionary
            2. (Google Sheets API) Retrieve newsletters from google sheets `News Reporter`
            3. (Google Email API) Retrieve all emails for the last X hours
            4. (Email Analyzer) Exapnd emails with extra information (body)
            5. (DataFrame Operations) Remove emails with empty body or empty category
            6. (Email Analyzer) Expand with (a) statistics (b) and body summary using OpenAI
            7. (DataFrame Operations) Open a new '.txt' file and for every email
                - Write the `subject`, the `from` and the generated summary in a bullet point approach
            8. (Google Docs API) Append the .txt file to google docs named `News Reporters`
            9. (Google Sheets API) Appends logs `logs` at Google Sheets
        """
        ## _____________________________________________________________________________________________________________________ ##
        ## 1. (DataFrame Operations) Initialize logs dictionary
        logs = {
            "exec_date"      : today.strftime('%Y-%m-%d'),
            "start_datetime" : (today - dt.timedelta(hours = hours)).strftime('%Y-%m-%d %H:%M:%S'),
            "end_datetime"   : today.strftime('%Y-%m-%d %H:%M:%S'),
            "period"         : hours
        }

        ## _____________________________________________________________________________________________________________________ ##
        ## 2. (Reporter) Initialize configs (a) Newsletters (b) Docs (c) Docs IDs
        config_newsletters, config_docs, config_docs_ids = self.reporter.get_config(
            sheets_reporter_id                     = sheets_reporter_id,
            sheets_reporter_tab_config_newsletters = sheets_reporter_tab_config_newsletters,
            sheets_reporter_tab_config_docs        = sheets_reporter_tab_config_docs,
            sheets_reporter_tab_config_docs_ids    = sheets_reporter_tab_config_docs_ids
        )
       
        ## _____________________________________________________________________________________________________________________ ##
        ## 3. (Reporter) Retrieve newsletters from google sheets `News Reporter`
        newsletters, newsletters_categories = self.reporter.get_config_enabled_newsletters(
            config_newsletters = config_newsletters
        )

        ## _____________________________________________________________________________________________________________________ ##
        ##  4. (Google Email API) Retrieve all emails for the last X hours
        emails = pd.DataFrame(
            self.google_email_api.get_emails_from_past_days(
                user_id   = 'me',
                num_hours = hours
            )
        )

        logs["num_emails"] = len(emails)

        ## _____________________________________________________________________________________________________________________ ##
        ##  5. (Email Analyzer) Exapnd emails with extra information (body)
        emails[['label_ids','date','subject', 'from','body','category']] = emails.progress_apply(
            lambda x : self.email_analyzer.expand_with_body_info(x, newsletters_categories),
            axis = 1
        ) 
        self.mk1.logging.logger.info(f"(Controller.run_get_emails) [# emails] [Initially] = {len(emails)}")
        
        ## _____________________________________________________________________________________________________________________ ##
        ## 6. (DataFrame Operations) Remove emails with empty body or empty category
        emails = emails[
            (~emails['body'].isin(self.__null_values)) |
            (~emails['category'].isin(self.__null_values))
        ]
        logs["num_emails_filtered"] = len(emails)
        self.mk1.logging.logger.info(f"(Controller.run_get_emails) [# emails] [Keeping only the newsletters interested] = {len(emails)}")

        ## _____________________________________________________________________________________________________________________ ##
        ## 7. (Email Analyzer) Expand with (a) statistics (b) and body summary using OpenAI
        emails[[ 'num_tokens_raw','body_clean','num_tokens_clean', 'body_clean_summarized','num_tokens_clean_summarized']] = emails.progress_apply(
            lambda x : self.email_analyzer.get_email_summary_and_statistics(x),
            axis = 1
        )

        logs["avg_num_tokens_raw"]          = emails["num_tokens_raw"].sum() /len(emails)
        logs["avg_num_tokens_clean"]        = emails["num_tokens_clean"].sum() /len(emails)
        logs["num_tokens_clean_summarized"] = emails["num_tokens_clean_summarized"].sum() /len(emails)

        ## _____________________________________________________________________________________________________________________ ##
        ## 8. (DataFrame Operations) Open a new '.txt' file and for every email : Write the `subject`, the `from` and the generated summary in a bullet point approach
        summary_per_category = self.reporter.write_summary_to_file(
            config_newsletters   = config_newsletters,
            newsletters          = newsletters,
            emails               = emails,
            fn_path_summary_txt  = fn_path_summary_txt,
            fn_path_summary_json = fn_path_summary_json
        )

        ## _____________________________________________________________________________________________________________________ ##
        ## 9. (Reporter) Append the .txt file to google docs named `(<Year> <Month>) Newsletters Summaries`
        doc_reporter_id = self.reporter.get_doc_reporter_id(
            today                           = today,
            config_docs                     = config_docs,
            config_docs_ids                 = config_docs_ids,
            sheets_reporter_id              = sheets_reporter_id,
            sheets_reporter_tab_config_docs = sheets_reporter_tab_config_docs
        )
        self.reporter.append_summary_to_doc_reporter(
            today                  = today,
            summary_per_category   = summary_per_category,
            doc_reporter_id        = doc_reporter_id,
            logs                   = logs,
        )

        ## _____________________________________________________________________________________________________________________ ##
        ## 10. (Google Sheets API) Appends logs `logs` at Google Sheets
        self.data_loader.append_data_to_google_sheets(
            df                     = pd.DataFrame(logs, index = [0]),
            spreadsheet_id         = sheets_reporter_id,
            spreadsheet_range_name = sheets_reporter_tab_logs,
        )

        ## _____________________________________________________________________________________________________________________ ##
        ## 11. (Telegram API) Send summary in telegram chat
        chat_ids = self.data_loader.load_data_from_google_sheets_tab(
            spreadsheet_id          = sheets_reporter_id,
            spreadsheet_range_name  = sheets_reporter_tab_config_telegram
        )
        self.telegram_api.set_data(
            summary_per_category = summary_per_category,
            today                = today,
            chat_ids             = chat_ids
        )
        self.telegram_api.run_daily_news_report(
        )


        ## _____________________________________________________________________________________________________________________ ##
        ## 12. (Google Email API) Delete all newsletters emails
        emails['archive_status'] = emails.progress_apply(
            lambda x : self.email_analyzer.archive_emails_after_summarizing(x),
            axis = 1
        )



    ## -------------------------------------------------------------------------------------------------------------------------------------------- ##
    def run(self):
        schedule_hour = int(self.args.schedule_hour)

        # initialize services
        self.run_initialization(enable_telegram = True)
        self.mk1.logging.logger.info(f"(Controller.run) All services initilalized")
        print(f"(Controller.run) All services initilalized")
        
        while True : 
            today = datetime.now()

            self.run_initialization(enable_telegram = False)
            self.mk1.logging.logger.info(f"(Controller.run) [Datetime = {today}, Schedule Time = {schedule_hour}] All services initilalized (except Telegram)")
            print(f"(Controller.run) [Datetime = {today}, Schedule Time = {schedule_hour}] All services initilalized (except Telegram)")
            if schedule_hour == today.hour : 
                self.mk1.logging.logger.info(f"(Controller.run) [Datetime = {today}, Schedule Time = {schedule_hour}] Report being generated ... ")
                print(f"(Controller.run) [Datetime = {today}, Schedule Time = {schedule_hour}] Report being generated ... ")
                self.run_get_email_report()

            time.sleep(60 * 60) # refreshing = 60 s * 60 min = every 1h check



if __name__ == '__main__':
    Controller(
        MkI.get_instance(_logging = True)
    ).run()
