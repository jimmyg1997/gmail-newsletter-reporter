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
from dateutil.relativedelta import relativedelta
from datetime               import datetime
from IPython.display        import display
from typing                 import Dict, Any, List

# -*-*-*-*-*-*-*-*-*-*-* #
#     Project Modules    #
# -*-*-*-*-*-*-*-*-*-*-* #
class DataLoader():
    def __init__(
            self,
            mk1,
            google_sheets_api = None
        ) :
        ## System Design
        self.mk1 = mk1

        ## Initializing Services
        self.google_sheets_api = google_sheets_api


    ## *-*-*-*-*-*-*-*-*-*-*- KIRBY  -*-*-*-*-*-*-*-*-*-*- ##
    def write_data_to_kirby(
            self,
            df          : pd.DataFrame,
            table_name  : str,
            casting_map : Dict[str, Any],
            file_path   : str ,
            time_sleep  : int = 5
        ):

        try :
            df     = self.kirby_api.fix_columns(df = df)
            df     = self.kirby_api.cast_to_hive_friendly_format(df = df, casting_map = casting_map)
            job_id = self.kirby_api.upload_to_hive(table_name = table_name, df = df, file_path = file_path)
            self.kirby_api.verify_job(job_id = job_id, table_name = table_name, time_sleep = time_sleep)
            self.mk1.logging.logger.info(f"(DataLoader.write_data_to_kirby) Data uploaded to Kirby table {table_name}")

        except Exception as e:
            self.mk1.logging.logger.error(f"(DataLoader.write_data_to_kirby) Data uploading to kirby table {table_name} failed: {e}")
            raise e



    ## *-*-*-*-*-*-*-*-*-*-*- QUERYRUNNER  -*-*-*-*-*-*-*-*-*-*- ##
    #@retry((queryrunner_client.lib.exceptions.ResultError),tries = 3, delay = 2)
    def load_data_from_query_atlantis(self, report_id : str = "", params : Dict[str, Any] = {}, datacenter : str = "phx2" ) :
        try :
            data, _ =  self.query_atlantis_api.run_query(report_id  = report_id, datacenter = datacenter, parameters = params)
            self.mk1.logging.logger.info("(DataLoader.load_data_from_query) Data Loaded")
            return data

        except Exception as e:
            self.mk1.logging.logger.error(f"(DataLoader.load_data_from_query) Data loading failed: {e}")
            raise e



    # @retry((queryrunner_client.lib.exceptions.ResultError),tries = 3, delay = 2)
    def load_data_from_query_neutrino(self, report_id : str = "", params : Dict[str, Any] = {}, datacenter : str = "phx2") :

        try :
            data, _ =  self.query_neutrino_api.run_query(report_id  = report_id, datacenter = datacenter, parameters = params)
            #data = self.query_nr.query_data(report_id = report_id, params = params)[0]
            self.mk1.logging.logger.info("(DataLoader.load_data_from_query_neutrino) Data Loaded")
            return data


        except Exception as e:
            self.mk1.logging.logger.error(f"(DataLoader.load_data_from_query_neutrino) Data loading failed: {e}")
            raise e

    ## *-*-*-*-*-*-*-*-*-*-*- GOOGLE DOCS -*-*-*-*-*-*-*-*-*-*- ##









    ## *-*-*-*-*-*-*-*-*-*-*- GOOGLE SHEETS -*-*-*-*-*-*-*-*-*-*- ##
    @retry((ValueError, TypeError, KeyError),tries = 3, delay = 2)
    def create_new_tab_to_google_sheets(
            self,
            spreadsheet_id       : str,
            spreadsheet_tab_name : str
        ) -> None :
        """ Creates new tab to a specific spreadsheet

            Args
            ____
                :param: spreadsheet_id (:obj: `str`)       - The id of the respective spreadsheet
                :param: spreadsheet_tab_name (:obj: `str`) - The name of the tab under the spreadsheet
                :returns:
        """
        try :
            self.google_sheets_api.create_spreadsheet_tab(spreadsheet_id = spreadsheet_id,spreadsheet_tab_name = spreadsheet_tab_name)
            self.mk1.logging.logger.info("(DataHandler.create_new_tab_to_google_sheets) New Tab created sucessfully")

        except Exception as e:
            self.mk1.logging.logger.error(f"(DataHandler.create_new_tab_to_google_sheets) New tab creation failed: {e}")
            raise e

    @retry((ValueError, TypeError, KeyError),tries = 3, delay = 2)
    def get_google_sheets_tab_num_rows(
            self,
            spreadsheet_id         : str,
            spreadsheet_range_name : str
        ) -> int :
        """ Retrieve number of rows os a specific google sheets tab

            Args
            ____
                :param: spreadsheet_id (:obj: `str`)         - The id of the respective spreadsheet
                :param: spreadsheet_range_name (:obj: `str`) - The range of the tab under the spreadsheet

        """
        try :
            num_rows = self.google_sheets_api.get_tab_num_dimension(spreadsheet_id, spreadsheet_range_name)
            self.mk1.logging.logger.info(f"(DataHandler.get_google_sheets_tab_num_rows) Tab {spreadsheet_range_name} has {num_rows} rows ")
            return num_rows

        except Exception as e:
            self.mk1.logging.logger.error(f"(DataHandler.get_google_sheets_tab_num_rows) Tab number of rows retrieval failed : {e}")
            raise e


    @retry((ValueError, TypeError, KeyError),tries = 3, delay = 2)
    def clear_google_sheets_tab(
            self,
            spreadsheet_id         : str,
            spreadsheet_range_name : str
        ) -> None :
        """ Clears a specific tab to a specific spreadsheet

            Args
            ____
                :param: spreadsheet_id (:obj: `str`)        - The id of the respective spreadsheet
                :param: spreadsheet_range_name (:obj: `str`) - The range of the tab under the spreadsheet

        """
        try :
            self.google_sheets_api.clear_tab(spreadsheet_id, spreadsheet_range_name)
            self.mk1.logging.logger.info("(DataHandler.clear_google_sheets_tab) Tab was cleared sucessfully")

        except Exception as e:
            self.mk1.logging.logger.error(f"(DataHandler.create_new_tab_to_google_sheets) Tab clearing failed: {e}")
            raise e


    def make_df_json_serializable(self, df : pd.DataFrame) -> pd.DataFrame :
        # Convert all timestamp columns to string
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            else :
                df[col] = df[col].astype(str)
        return df


    @retry((ValueError, TypeError, KeyError),tries = 3, delay = 2)
    def write_data_to_google_sheets(
            self,
            df                      : pd.DataFrame,
            spreadsheet_id          : str,
            spreadsheet_range_name  : str,
            spreadsheet_has_index   : bool = False,
            spreadsheet_has_headers : bool = False
        ) -> None :
        """ The function writes data to specific tab  range of a specific spreadsheet (overwrites if data already exist).

            Args
            ____

                :param: df (:obj: `pd.DataFrame`)            - The data that will be pushed to a specicifc tab of the spreadsheet
                :param: spreadsheet_id (:obj: `str`)         - The id of the respective spreadsheet
                :param: spreadsheet_range_name (:obj: `str`) - The range of the tab under the spreadsheet
                :param: spreadsheet_has_index (:obj: `bool`) - Whether we want to push the dataframe along with its index
                :param: spreadsheet_has_headers (:obj: `bool`) - Whether we want to push the dataframe along with its headers

        """

        df = self.make_df_json_serializable(df)

        try :
            self.google_sheets_api.clear_tab(
                spreadsheet_id          = spreadsheet_id,
                spreadsheet_range_name  = spreadsheet_range_name
            )
            self.google_sheets_api.write_df_to_tab(
                df                      = df,
                spreadsheet_id          = spreadsheet_id,
                spreadsheet_range_name  = spreadsheet_range_name,
                spreadsheet_has_index   = spreadsheet_has_index,
                spreadsheet_has_headers = spreadsheet_has_headers
            )
            self.mk1.logging.logger.info("(DataHandler.write_data_to_google_sheets) Data Uploaded")


        except Exception as e:
            self.mk1.logging.logger.error(f"(DataHandler.write_data_to_google_sheets) Data uploading to google sheets failed: {e}")

            raise e

    @retry((ValueError, TypeError, KeyError),tries = 3, delay = 2)
    def append_data_to_google_sheets(
            self,
            df                      : pd.DataFrame,
            spreadsheet_id          : str,
            spreadsheet_range_name  : str,
            spreadsheet_has_index   : bool = False,
            spreadsheet_has_headers : bool = False,
            dimension               : str = "ROWS"
        ) -> None :
        """ The function appends data to a specific tab range of a specific spreadsheet. Appends either vertically or horizontally

            Args
            ____
                :param: df (:obj: `pd.DataFrame`)              - The data that will be pushed to a specicifc tab of the spreadsheet
                :param: spreadsheet_id (:obj: `str`)           - The id of the respective spreadsheet
                :param: spreadsheet_range_name (:obj: `str`)   - The range of the tab under the spreadsheet
                :param: spreadsheet_has_index (:obj: `bool`)   - Whether we want to push the dataframe along with its index
                :param: spreadsheet_has_headers (:obj: `bool`) - Whether we want to push the dataframe along with its headers
                :param: dimension (:obj: `str`)                - Options = {"ROWS", "COLUMNS"} whether to append data vertically or horizontally, respecively

        """
        df = self.make_df_json_serializable(df)

        try :

            if dimension == "ROWS" :
                self.google_sheets_api.append_rows_to_tab(
                    df                      = df,
                    spreadsheet_id          = spreadsheet_id,
                    spreadsheet_range_name  = spreadsheet_range_name,
                    spreadsheet_has_index   = spreadsheet_has_index,
                    spreadsheet_has_headers = spreadsheet_has_headers
                )

            elif dimension == "COLUMNS" :
                self.google_sheets_api.append_columns_to_tab(
                    df                      = df,
                    spreadsheet_id          = spreadsheet_id,
                    spreadsheet_range_name  = spreadsheet_range_name,
                    spreadsheet_has_index   = spreadsheet_has_index,
                    spreadsheet_has_headers = spreadsheet_has_headers
                )


            self.mk1.logging.logger.info("(DataHandler.append_data_to_google_sheets) Data Appended ")


        except Exception as e:
            self.mk1.logging.logger.error(f"(DataHandler.append_data_to_google_sheets) Data appending to google sheets failed: {e}")
            raise e

    @retry((ValueError, TypeError, KeyError),tries = 3, delay = 2)
    def load_data_from_google_sheets_tab(
            self,
            spreadsheet_id          : str,
            spreadsheet_range_name  : str,
            spreadsheet_has_index   : bool = False,
            spreadsheet_has_headers : bool = True
        ) -> pd.DataFrame :
        """ The function returns the data (in a dataframe format) from a specific tab of a specific spreadsheet

			Args
            ____
                :param: spreadsheet_id (:obj: `str`)           - The id of the respective spreadsheet
				:param: spreadsheet_range_name (:obj: `str`)   - The range of the tab under the spreadsheet
                :param: spreadsheet_has_index (:obj: `bool`)   - Whether we want to push the dataframe along with its index
                :param: spreadsheet_has_headers (:obj: `bool`) - Whether we want to push the dataframe along with its headers
				:returns: data (:obj: `pd.DataFrame`) - The data that will be pushed to a specicifc tab of the spreadsheet

        """

        try :
            data = self.google_sheets_api.get_df_from_tab(
                spreadsheet_id          = spreadsheet_id,
                spreadsheet_range_name  = spreadsheet_range_name,
                spreadsheet_has_index   = spreadsheet_has_index,
                spreadsheet_has_headers = spreadsheet_has_headers
            )
            self.mk1.logging.logger.info(f"(DataHandler.get_number_of_google_sheets_tab) Tab exists.{data.shape[0]} rows {data.shape[1]} columns retrieved successfully")
            return data

        except Exception as e:
            self.mk1.logging.logger.error(f"(DataHandler.get_number_of_google_sheets_tab) Tab or spreadsheet does not exist. Rows were not retrieval failed: {e}")
            raise e


    def get_tab_url_from_google_sheets(
           self,
           spreadsheet_id       : str,
           spreadsheet_tab_name : str
        ) -> str :

        """
            The function returns the url for a specific tab under a specific spreadsheet

            Args
            ----
                :param: spreadsheet_id (:obj: `str`)       - The id of the respective spreadsheet
                :param: spreadsheet_tab_name (:obj: `str`) - The name of the tab under the spreadsheet
                :param: url (:obj: `str`)                  - The url of the specific tab

        """


        try :
            url = self.google_sheets_api.get_tab_url(
                spreadsheet_id       = spreadsheet_id,
                spreadsheet_tab_name = spreadsheet_tab_name
            )
            self.mk1.logging.logger.info("(DataHandler.get_tab_url_from_google_sheets) Tab URL is retrieved successfully")
            return url

        except Exception as e:
            self.mk1.logging.logger.error(f"(DataHandler.get_tab_url_from_google_sheets)Tab URL retrieval failed : {e}")
            raise e
