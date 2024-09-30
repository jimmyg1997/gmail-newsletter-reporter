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
import os, json
import numpy    as np
import pandas   as pd
import datetime as dt
from retry                  import retry
from tqdm                   import tqdm
from datetime               import datetime
from IPython.display        import display
from typing                 import Dict, Any, List
from dateutil.relativedelta import relativedelta
from tabulate               import tabulate


# -*-*-*-*-*-*-*-*-*-*-* #
#     Project Modules    #
# -*-*-*-*-*-*-*-*-*-*-* #
class Reporter():
    def __init__(
            self,
            mk1,
            google_sheets_api = None,
            google_docs_api   = None,
            google_drive_api  = None
        ) :
        self.mk1 = mk1

        ## __________ *** Initializing (client) *** __________
        self.google_sheets_api = google_sheets_api
        self.google_docs_api   = google_docs_api
        self.google_drive_api  = google_drive_api

        # __________ *** Initializing (attributes) *** __________
        self.__null_values = [
            None, np.nan, "", "#N/A", "null", "nan", "NaN"
        ]


    def get_config(
            self,
            sheets_reporter_id,
            sheets_reporter_tab_config_newsletters : str,
            sheets_reporter_tab_config_docs        : str, 
            sheets_reporter_tab_config_docs_ids    : str
        ) -> List[pd.DataFrame]:

        """ (Google Sheets API) Retrieve all configs from Google Sheets 'Gmail Newsletter Reporter'""" 
        try :
            config_newsletters = self.google_sheets_api.get_df_from_tab(
                spreadsheet_id          = sheets_reporter_id,
                spreadsheet_range_name  = sheets_reporter_tab_config_newsletters,
                spreadsheet_has_index   = False
            )

            config_docs = self.google_sheets_api.get_df_from_tab(
                spreadsheet_id          = sheets_reporter_id,
                spreadsheet_range_name  = sheets_reporter_tab_config_docs,
                spreadsheet_has_index   = False
            )

            config_docs_ids = self.google_sheets_api.get_df_from_tab(
                spreadsheet_id          = sheets_reporter_id,
                spreadsheet_range_name  = sheets_reporter_tab_config_docs_ids,
                spreadsheet_has_index   = False
            )

            config = [
                config_newsletters, 
                config_docs,
                config_docs_ids
            ]

            self.mk1.logging.logger.info(f"(Reporter.get_config) All config dataframes (newsletters, docs, docs_ids) were retrieved succesfully")
            return config

        except Exception as e:
            self.mk1.logging.logger.error(f"(Reporter.get_config) Retrieving all config dataframes (newsletters, docs, docs_ids) failed: {e}")
            raise e


        
    # ___________________________ (config) Newsletters Summaries ____________________________________ #

    def write_summary_to_file(
        self,
        config_newsletters   : pd.DataFrame,
        newsletters          : Dict[str, str],
        emails               : pd.DataFrame,
        fn_path_summary_txt  : str,
        fn_path_summary_json : str,
        include_subject      : bool = False,
        include_from         : bool = True,
        include_date         : bool = False,
        include_summary      : bool = True
    ) -> None:
        """
        Writes summaries of emails categorized by newsletter fields to a specified summary file.

            Parameters:
            - config_newsletters (pd.DataFrame): DataFrame containing newsletter configuration, including categories.
            - newsletters (Dict[str, str]): Dictionary where keys are categories, and values are newsletter names.
            - emails (pd.DataFrame): DataFrame containing email data, including subject, from, body_clean_summarized, and category.
            - fn_path_summary_txt (str): Path to the .txt file where summaries will be appended.
            - fn_path_summary_json (str): Path to the .json file where summaries will be appended.

            Returns:
            - None: The function writes to the file and logs success or failure messages.
            
            Raises:
            - Exception: If any error occurs during the writing process, it will be logged and re-raised.
        """
        try:
            summary_per_category = {
                category: [] for category in config_newsletters['Field'].unique()
            }

            with open(fn_path_summary_txt, 'w+') as file:
                for category in newsletters.keys():
                    emails_category = emails[emails['category'] == category].reset_index()

                    if not emails_category.empty:
                        file.write(f"<category>{category}<category>\n")

                        for idx, email in emails_category.iterrows():
                            print(f"[{category}] [{idx + 1}/{len(emails_category)}] Processing ...")

                            email_str    = ""

                            subject_str  = f"𝗦𝗨𝗕𝗝𝗘𝗖𝗧 : {email['subject']}\n"
                            from_str     = f"𝐅𝐑𝐎𝐌 : {email['from']}\n"
                            date_str     = f"𝐃𝐀𝐓𝐄 : {dt.datetime.utcfromtimestamp(int(email['date']) / 1000)}\n\n"
                            summary_str  = ''.join([f'{item}\n' for item in email['body_clean_summarized']])
                            

                            if include_subject : 
                                email_str += subject_str
                                file.write(subject_str) # Write to file

                            if include_from : 
                                email_str += from_str
                                file.write(from_str) # Write to file

                            if include_date : 
                                email_str += date_str
                                file.write(date_str) # Write to file

                            if include_summary : 
                                email_str += summary_str 
                                file.write(summary_str) # Write to file
 
                            email_str += "\n"
                            summary_per_category[category].append(email_str)                            

            with open(fn_path_summary_json, 'w') as file:
                json.dump(summary_per_category, file, indent = 4)  # indent for pretty printing

            self.mk1.logging.logger.info("(Reporter.write_summary_to_file) Appending summaries to file was successful")
            return summary_per_category

        except Exception as e:
            self.mk1.logging.logger.error(f"(Reporter.write_summary_to_file) Failed to append summaries: {e}")
            raise e



    # ___________________________ (config) Newsletters ____________________________________ #
    def _parse_categories_dataframe_into_dict(
            self,
            df : pd.DataFrame
        ) -> pd.DataFrame:

        newsletters = {}
        for index, row in df.iterrows():
            field      = row['Field']
            newsletter = row['Newsletter']
            email      = row['Email']

            if field not in newsletters:
                newsletters[field] = {}

            newsletters[field][newsletter] = email
        return newsletters


    def _generate_categories_mapping(
            self,
            newsletters : Dict
        ) :
        new_dict = dict()
        for category, newsletters_info in newsletters.items():
            for email in newsletters_info.values():
                new_dict[email] = category
        return new_dict

    def get_config_enabled_newsletters(
            self,
            config_newsletters : pd.DataFrame
        ) -> pd.DataFrame:
        """ (Google Sheets API) Retrieve newsletters from google sheets `News Reporter`""" 
        try :

            config_newsletters = config_newsletters[
                config_newsletters['Enabled'] == "TRUE"
            ]

            newsletters = self._parse_categories_dataframe_into_dict(
                df = config_newsletters
            )

            newsletters_categories = self._generate_categories_mapping(
                newsletters = newsletters
            )

            self.mk1.logging.logger.info(f"(Reporter.get_config_enabled_newsletters) Newsletters Config was retrieved succesfully")
            return newsletters, newsletters_categories

        except Exception as e:
            self.mk1.logging.logger.error(f"(Reporter.get_config_enabled_newsletters) Newsletters Config retrieval failed: {e}")
            raise e



    # ___________________________ (config) Docs ____________________________________ #
    def check_if_exists(self):
        pass



    def get_doc_reporter_id(
            self,
            today                           : dt.datetime,
            config_docs                     : pd.DataFrame,
            config_docs_ids                 : pd.DataFrame,
            sheets_reporter_id              : str,
            sheets_reporter_tab_config_docs : str
        ) -> str:
        """ Get the reporter id of the respective month """
        try :

            doc_id = config_docs.loc[
                config_docs['Datestr'] == today.replace(day = 1).strftime('%Y-%m-%d'),
                "Doc ID"
            ].values[0]

            if doc_id in self.__null_values : # Entering new month
                docs_id_template = config_docs_ids.loc[0, "Google Docs ID (template)"] 
                folder_id        = config_docs_ids.loc[0, "Google Drive Folder ID"]

                result = self.google_drive_api.copy_file(
                    file_id       = docs_id_template,
                    parent_folder = folder_id
                )

                doc_id   = result['copy_id']
                doc_name = result['copy_name']

                self.google_drive_api.change_file_name(
                    file_id  = doc_id,
                    new_name = doc_name\
                        .replace("Copy of ", "")\
                        .replace("<Year>", today.strftime("%Y"))\
                        .replace("<Month>", today.strftime("%B"))
                )

                config_docs.loc[
                    config_docs['Datestr'] == today.replace(day = 1).strftime('%Y-%m-%d'),
                    "Doc ID"
                ] = doc_id

                self.google_sheets_api.write_df_to_tab(
                    df                     = config_docs,
                    spreadsheet_id         = sheets_reporter_id,
                    spreadsheet_range_name = sheets_reporter_tab_config_docs
                )
            self.mk1.logging.logger.info(f"(Reporter.get_doc_reporter_id) ID was retrieved successfully. Docs ID = {doc_id} ")
            return doc_id

        except Exception as e:
            self.mk1.logging.logger.error(f"(Reporter.get_doc_reporter_id) Google Docs ID retrieval failed failed: {e}")
            raise e


    def _append_header_to_doc_reporter(
            self, 
            today : dt.datetime,
            doc_reporter_id: str
        ) -> None:
        try : 
            header = today.strftime('%Y-%m-%d') + "\n"
            all_text_content = self.google_docs_api.get_document(
                document_id = doc_reporter_id
            )
            self.google_docs_api.append_text_to_document(
                document_id  = doc_reporter_id,
                text_content = header,
                start_index  = all_text_content['content'][-1]['endIndex'] - 1,
                heading_id   = "HEADING_1",
            )
            self.mk1.logging.logger.info(f"(Reporter._append_header_to_doc_reporter) Appending the header {header} to doc ID : {doc_reporter_id} was successful")

        except Exception as e:
            self.mk1.logging.logger.error(f"(Reporter._append_header_to_doc_reporter) Appending the header to doc ID : {doc_reporter_id} failed: {e}")
            raise e

    def _append_summary_to_doc_reporter(
            self, 
            #fn_path_summary: str,
            summary_per_category : Dict[str,str],
            doc_reporter_id      : str
        ) -> None:
        try : 
            # with open(fn_path_summary, 'r') as file:
            #     summary = file.read()

            for category, summary in summary_per_category.items():
                start_index = self.google_docs_api.get_document(
                    document_id = doc_reporter_id
                )['content'][-1]['endIndex'] - 1

                self.google_docs_api.append_text_to_document(
                    document_id  = doc_reporter_id,
                    text_content = category + "\n",
                    start_index  = start_index,
                    heading_id   = "HEADING_3", # "NORMAL_TEXT"
                    bold         = True,
                    #font_size    = 14
                )

                if len(summary) > 0 : 
                    for summary_part in summary : 
                        start_index = self.google_docs_api.get_document(
                            document_id = doc_reporter_id
                        )['content'][-1]['endIndex'] - 1

                        self.google_docs_api.append_text_to_document(
                            document_id  = doc_reporter_id,
                            text_content = summary_part,
                            start_index  = start_index,
                            heading_id   = "NORMAL_TEXT"
                        )
                        


            # self.google_docs_api.append_text_to_document(
            #     document_id  = doc_reporter_id,
            #     text_content = summary,
            #     start_index  = all_text_content['content'][-1]['endIndex'] - 1,
            #     heading_id   = "NORMAL_TEXT"
            # )
            self.mk1.logging.logger.info(f"(Reporter._append_summary_to_doc_reporter) Appending text to doc ID : {doc_reporter_id} was successful")

        except Exception as e:
            self.mk1.logging.logger.error(f"(Reporter._append_summary_to_doc_reporter) Appending text to doc ID : {doc_reporter_id} failed: {e}")
            raise e



    def _format_as_plain_table(
            self,
            df : pd.DataFrame
        ) -> str :
        """ Convert the DataFrame to a properly aligned string table """
        # Convert the DataFrame to a properly aligned plain text table string
        headers = ["Key", "Value"]
        col_widths = [
            max(len(str(index)) for index in df.index),  # Width for 'Key' column
            max(len(str(val)) for val in df['Value'])   # Width for 'Value' column
        ]

        # Build the header line and separator
        header_line = " | ".join(f"{headers[i].ljust(col_widths[i])}" for i in range(len(headers)))
        separator_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

        # Build each row
        row_lines = []
        for index, row in df.iterrows():
            row_str = " | ".join(f"{str(index).ljust(col_widths[0])} | {str(row['Value']).ljust(col_widths[1])}")
            row_lines.append(row_str)

        # Combine everything into a formatted table string
        fancy_table = f"{header_line}\n{separator_line}\n" + "\n".join(row_lines)

        return fancy_table


    def _format_df_for_google_docs(
            self,
            data_dict  : Dict[str,str],
            method     : str = "tabulate",
            tablefmt   : str = "heavy_grid"
        ):

        data_df = pd.DataFrame(
            data_dict, 
            index = ['Value']
        ).T 

        if method == "plain_table" : 
            content = self._format_as_plain_table(
                df = data_df 
            )

        elif method == "tabulate" :
            content = tabulate(
                tabular_data = data_df, 
                headers      = 'keys', 
                tablefmt     = tablefmt
            )

        elif method == "json" :
            content = json.dumps(
                obj       = data_dict, 
                indent    = 4,
                sort_keys = True
            )

        return content + "\n"



    def _append_logs_to_doc_reporter(
            self, 
            logs            : Dict[str,str],
            doc_reporter_id : str,
            method          : str = "tabulate",
            tablefmt        : str = "presto",
        ) -> None:
        try : 
            text_content = self._format_df_for_google_docs(
                data_dict = logs,
                method    = method,
                tablefmt  = tablefmt
            )

            all_text_content = self.google_docs_api.get_document(
                document_id = doc_reporter_id
            )
            self.google_docs_api.append_text_to_document(
                document_id  = doc_reporter_id,
                text_content = text_content,
                start_index  = all_text_content['content'][-1]['endIndex'] - 1,
                heading_id   = "NORMAL_TEXT",
                font_family  = "Courier New"
            )
            
            self.mk1.logging.logger.info(f"(Reporter._append_logs_to_doc_reporter) Appending the logs to doc ID : {doc_reporter_id} was successful")

        except Exception as e:
            self.mk1.logging.logger.error(f"(Reporter._append_logs_to_doc_reporter) Appending the logs to doc ID : {doc_reporter_id} failed: {e}")
            raise e

    def append_summary_to_doc_reporter(
            self,
            today                : dt.datetime, 
            #fn_path_summary : str, 
            doc_reporter_id      : str,
            summary_per_category : Dict[str,str],
            logs                 : pd.DataFrame,
            method               : str = "tabulate",
            tablefmt             : str = "presto"
        ) -> None:
        """ Append summary text to current document 
            (Google Docs API) Append the .txt file to google docs named `(<Year> <Month>) Newsletters Summaries`

        """
        try :
            self._append_header_to_doc_reporter(
                today           = today,
                doc_reporter_id = doc_reporter_id
            )

            self._append_logs_to_doc_reporter(
                logs            = logs,
                doc_reporter_id = doc_reporter_id,
                method          = method,
                tablefmt        = tablefmt
            )
            self._append_summary_to_doc_reporter(
                #fn_path_summary = fn_path_summary,
                summary_per_category = summary_per_category,
                doc_reporter_id      = doc_reporter_id
            )
            
            self.mk1.logging.logger.info(f"(Reporter.append_text_to_doc) Appending text to doc ID : {doc_reporter_id} was successful")

        except Exception as e:
            self.mk1.logging.logger.error(f"(Reporter.append_text_to_doc) Appending text to doc ID : {doc_reporter_id} failed: {e}")
            raise e





