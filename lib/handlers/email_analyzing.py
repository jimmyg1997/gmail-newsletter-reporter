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
    """
    This class is designed to analyze emails, extract content, summarize them, and perform
    certain actions such as deletion or obtaining email statistics.
    
    Attributes:
        mk1 (object): The system design object.
        google_email_api (object): The Google Email API object for email interaction.
        openai_api (object): The OpenAI API object for text summarization.
    """
    def __init__(
            self,
            mk1,
            google_email_api = None,
            openai_api       = None
        ) :
        """
        Initializes the EmailAnalyzer class with necessary API objects.
        
        Args:
            mk1 (object): System design object for interaction.
            google_email_api (object, optional): Google Email API instance.
            openai_api (object, optional): OpenAI API instance.
        """
        ## System Design
        self.mk1 = mk1

        ## *-*-*-*-* Initializing Service(s) *-*-*-*-* ##
        self.google_email_api = google_email_api
        self.openai_api = openai_api


    def archive_emails_after_summarizing(
            self,
            row : Dict[str,Any],
        ) -> str:
        """
        Deletes an email after summarizing its contents.
        
        Args:
            row (dict): A dictionary containing email information.
        
        Returns:
            str: Response from the delete action.
        """
        try : 
            archive_status = self.google_email_api.archive_email_by_id(
                user_id  = 'me',
                email_id = row['id']
            )
            return archive_status

        except Exception as e :
            raise e


    def expand_with_body_info(
            self,
            row                    : Dict[str,Any],
            newsletters_categories : Dict[str,str]
        ) -> pd.Series:
        """
        Expands email data with body and category information.
        
        Args:
            row (dict): The email row containing basic information.
            newsletters_categories (dict): Mapping of sender email to category.
        
        Returns:
            pd.Series: A Pandas Series with the expanded information (label_ids, date, subject, sender, body, category).
        """
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
        ) -> str:
        """
        Extracts meaningful content from HTML by removing unwanted tags.

        Args:
            html_text (str): The HTML content to clean and extract from.

        Returns:
            str: Cleaned text content extracted from HTML.
        """
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


    def remove_urls_and_patterns(self, text: str) -> str:
        """
        Removes URLs and unwanted patterns from text.

        Args:
            text (str): The raw text to clean from URLs and patterns.

        Returns:
            str: Cleaned text without URLs or unwanted characters.
        """
        # Decode URL-encoded characters
        decoded_text = unquote(text)

        # Define a regular expression pattern to match URLs
        url_pattern = re.compile(r'https?://\S+|www\.\S+')

        # Use sub() method to replace matched URLs with an empty string
        text_without_urls = url_pattern.sub('', decoded_text)

        return text_without_urls


    def get_email_summary_and_statistics(
            self,
            row: Dict[str, Any]
        ) -> pd.Series:
        """
        Summarizes an email's body and generates token statistics.
        
        Args:
            row (dict): A dictionary containing email details, including the body.
        
        Returns:
            pd.Series: A Pandas Series with raw token count, cleaned body, cleaned token count, summarized body, and summarized token count.
        """
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