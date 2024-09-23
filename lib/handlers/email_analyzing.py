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
from typing                 import Dict, Any, List
from concurrent.futures     import ThreadPoolExecutor

# -*-*-*-*-*-*-*-*-*-*-* #
#   Third-Party Modules  #
# -*-*-*-*-*-*-*-*-*-*-* #
from bs4  import BeautifulSoup


class EmailAnalyzer():
    def __init__(
            self,
            mk1,
            google_email_api = None,
            openai_api       = None
        ) :
        ## System Design
        self.mk1 = mk1

        ## *-*-*-*-* Initializing Service(s) *-*-*-*-* ##
        self.google_email_api = google_email_api
        self.openai_api = openai_api


    def expand_with_body_info(
            self,
            row                    : Dict[str,Any],
            newsletters_categories : Dict[str,str]
        ) :
        try :
            info = self.google_email_api.get_email_text_info(
                user_id  = 'me',
                email_id = row['id']
            )
            if 'body' in info and info['body'] and 'from' in info :
                if info['from'] in newsletters_categories.keys() :
                    return pd.Series([
                        info['label_ids'],
                        info['date'],
                        info['subject'],
                        info['from'],
                        info['body'],
                        newsletters_categories[info['from']]
                    ])
            return pd.Series([''] * 6)

        except Exception as e :
            raise e
            return pd.Series([''] * 6)

    def extract_content(
            self,
            html_text : str
        ):
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(html_text, 'html.parser')
        # Remove unwanted elements such as footer, subscribe, etc.
        unwanted_tags = ['footer', 'subscribe', 'unwanted-class', 'another-unwanted-class']
        for tag in unwanted_tags:
            for unwanted_elem in soup.find_all(tag):
                unwanted_elem.extract()

        # Extract text content while preserving structure
        cleaned_text = soup.get_text(
            separator = '\n',
            strip     = True
        )
        return cleaned_text


    def remove_urls_and_patterns(self, text):
        # Decode URL-encoded characters
        decoded_text = unquote(text)

        # Define a regular expression pattern to match URLs
        url_pattern = re.compile(r'https?://\S+|www\.\S+')

        # Use sub() method to replace matched URLs with an empty string
        text_without_urls = url_pattern.sub('', decoded_text)

        return text_without_urls



    def get_email_summary_and_statistics(
            self,
            row
        ):
        try :
            num_tokens_raw = len(
                row['body'].split(" ")
            )

            body_clean = self.extract_content(
                html_text = row['body']
            )

            body_clean = self.remove_urls_and_patterns(
                text = body_clean
            )

            num_tokens_clean = len(
                body_clean.split(" ")
            )

            body_clean_summarized = self.openai_api.generate_summary(
                text = body_clean
            )
            time.sleep(2)

            num_tokens_clean_summarized = len(
                " ".join(body_clean_summarized).split(" ")

            )

            return pd.Series([
                num_tokens_raw,
                body_clean,
                num_tokens_clean,
                body_clean_summarized,
                num_tokens_clean_summarized
            ])

        except Exception as e :
            raise e
            return pd.Series([''] * 5)
