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
import os, json, re
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
import openai
import tiktoken
import langid
from openai    import OpenAI
from bs4       import BeautifulSoup


class OpenaiAPI():
    def __init__(
            self,
            mk1
        ) :
        ## System Design
        self.mk1 = mk1

        ## __________ *** Initializing (attributes) *** _______
        self.token_key = str(self.mk1.config.get("api_openai","token_key"))

        ## __________ *** Initializing (client) *** __________
        self.service = self.build_client()


    # Service
    def build_client(self):
        try:
            # Creating the OpenAI API client
            service = OpenAI(
                api_key = self.token_key
            )
            self.mk1.logging.logger.info("(OpenaiAPI.build_client) Service build succeeded")
            return service

        except Exception as e:
            self.mk1.logging.logger.error(f"(OpenaiAPI.build_client) Service build failed: {e}")
            raise e
            return None



    def split_into_chunks(
            self,
            text   : str,
            tokens : int = 3000
        ):
        encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')
        words = encoding.encode(text)
        chunks = []
        for i in range(0, len(words), tokens):
            chunks.append(' '.join(encoding.decode(words[i:i + tokens])))
        return chunks



    def generate_summary(
            self,
            text      : str,
            threshold : int = 7
        ):

        chunks = self.split_into_chunks(
            text = text
        )

        # Processes chunks in parallel
        with ThreadPoolExecutor() as executor:
            responses = list(executor.map(self.generate_summary_chunk, chunks))

        #responses = ".".join(responses)
        #responses = responses.split(".")
        responses = [
            s for s in responses if len(s.split()) >= threshold
        ]

        return responses


    def get_prompt(
            self,
            text                   : str,
            lower_limit_word_count : int = 20,
            upper_limit_word_count : int = 30,
            pct_of_text_to_keep    : int = 5
        ) -> Tuple[str, str]:
        """ Determines the appropriate prompt and system content based on the language of the input text. 
            Instructions that can be added
            __
            * Strictly keep lanaguge of summary same as language of the provided text.
            * Keep the total number of output words to {pct_of_text_to_keep} % percent of the total number of input text.
            * Keep the total number of output words betweem ({lower_limit_word_count}, {upper_limit_word_count})
        """

        NAME_PREFIX = "Your name is AI player and you are acting"
        PROMPT = NAME_PREFIX + f"""as a professional summarizer,
            you have the ability to create a concise and comprehensive summary of the provided text.
            You could detect the language of input text and output the summary in the same language.
            Now you need to follow these guidelines carefully and provide the summary for input text.
            * Language of the summary should always be English, but always show names and namespaces in the original language and English.
            * Craft a concise summary focusing on the most essential information, avoiding unnecessary detail or repetition.
            * Incorporate main ideas and essential information, eliminating extraneous language and focusing on critical aspects.
            * Rely strictly on the provided text, without including external information.
            * Do not eliminate numbers that are crucial as evidence data.
            * Ensure that the summary is professional and friendly for human reading.
            * Concat similar ideas into a cohesive narrative.
            * Do not use italic, bold, or underline anywhere.
            * Summarize in 1  paragraph and 3 sentence. Maximum of {upper_limit_word_count} words
            * Add 4 topics as hashtags in the end after the summary
            * Add emojis!

            ## Input text: {text}
        """
        return PROMPT


    def select_prompt_based_on_language(
            self,
            text: str,
            lower_limit_word_count: int = 90,
            upper_limit_word_count: int = 110
        ) -> Tuple[str, str]:
        """ Determines the appropriate prompt and system content based on the language of the input text.
        
            Supported languages:
            ____
            af, am, an, ar, as, az, be, bg, bn, br, bs, ca, cs, cy, da, de, dz, el, en, eo, es, et, eu, fa, fi, fo, fr, ga, gl, gu, he, hi,
            hr, ht, hu, hy, id, is, it, ja, jv, ka, kk, km, kn, ko, ku, ky, la, lb, lo, lt, lv, mg, mk, ml, mn, mr, ms, mt, nb, ne, nl, nn,
            no, oc, or, pa, pl, ps, pt, qu, ro, ru, rw, se, si, sk, sl, sq, sr, sv, sw, ta, te, th, tl, tr, ug, uk, ur, vi, vo, wa, xh, zh, zu
        """
        lang, _        = langid.classify(text)
        prompt         = None
        system_content = None
        if lang == "el":
            prompt = (
                f"Δημιούργησε μια περίληψη {lower_limit_word_count}-{upper_limit_word_count} λέξεων, "
                "με τα πιο σημαντικά σημεία του ακόλουθου κειμένου, σε μια σύντομη και περιεκτική παράγραφο. "
                "Απόφυγε τις εισαγωγικές προτάσεις και πρόσθεσε emojis. Το κείμενο:"
            )
            system_content = (
                f"Δημιουργήστε μια πλήρη απάντηση σε {lower_limit_word_count} έως {upper_limit_word_count} "
                "λέξεις, με τα πιο σημαντικά σημεία του ακόλουθου κειμένου, σε μια σύντομη και περιεκτική παράγραφο. "
                "Απόφυγε τις εισαγωγικές προτάσεις και πρόσθεσε emojis."
            )
        elif lang in {"uk", "an", "en"}:
            prompt = (
                f"Summarize the key points of the following text in {lower_limit_word_count}-{upper_limit_word_count} "
                "words within a concise paragraph. Avoid introductory sentences and include emojis. The text:"
            )
            system_content = (
                f"Generate a summary in {lower_limit_word_count} to {upper_limit_word_count} words, focusing on the key points "
                "of the following text in a concise paragraph. Avoid introductory sentences and include emojis."
            )
        return prompt, system_content



    def generate_summary_chunk(
            self,
            text : str
        ):
        """ Generates a summary of the input text using the GPT model.

            Parameters
            ----------
            text : str
                The text to be summarized.

            Returns
            -------
            str
                The generated summary of the input text. If no summary can be generated, returns 'EMPTY'.

            Notes
            -----
            * Summarizes news article titles or similar content in 40 to 50 words.
            * Summaries are returned in paragraph format, not in list format.
            * If a summary cannot be generated, the word 'EMPTY' is returned.
            * https://community.openai.com/t/asking-for-a-summary-of-news-article-titles-and-chat-completion-is-not-able-to-summarise/288015/9

            Raises
            ------
            openai.OpenAIError
                If an error occurs while initializing the OpenAI API or generating a response.
        """

        try :
            # Give the prompt for summarization
            # prompt_prefix, system_content = self.select_prompt_based_on_language(
            #     text = text
            # )
            # prompt = f"{prompt_prefix}\n{text}\n"

            prompt = self.get_prompt(
                text = text
            )

            messages = [
                # {'role': 'system', 'content': system_content},
                {'role': 'user',   'content': prompt}
            ]
            response = self.service.chat.completions.create(
                model       = "gpt-3.5-turbo-0125",
                messages    = messages,
                temperature = 0.8,
                max_tokens  = 500,
                n           = 1,
                stop        = None,
                # max_tokens       = 300,
                # top_p             = 1,
                # frequency_penalty = 0.0,
                # presence_penalty  = 0.0,
                # stop              = ["\n"]
            )

            self.mk1.logging.logger.info(f"(OpenaiAPI.generate_summary_chunk) Summary was generated successfully")
            # Extract the generated content from the response
            return response.choices[0].message.content.strip()

        except openai.OpenAIError as e:
            self.mk1.logging.logger.error(f"(OpenaiAPI.generate_summary_chunk) Error occurred while initializing OpenAI API: {e}")
            raise e
            return None
