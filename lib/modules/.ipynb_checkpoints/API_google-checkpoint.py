# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    [*] Description : Py3 wrapper for Google API
    [*] Author      : dimitrios.georgiou@uber.com 
    [*] Date        : Apr, 2021
    [*] Links       :  
    [*] Google APIs supported so far : 
        - Google Sheets API
        - Google Email API
        - Google Drive API
"""

# -*-*-*-*-*-*-*-*-*-*-* #
#     Basic Modules      #
# -*-*-*-*-*-*-*-*-*-*-* #
import requests
import pickle
import os
import json
import yaml
import time
import requests
import codecs
import pandas as pd
import base64
from base64   import urlsafe_b64encode
from datetime import datetime, timedelta
from typing   import Callable, Dict, Generic, Optional, Set, Tuple, TypeVar, Deque, List


# -*-*-*-*-*-*-*-*-*-*-* #
#      API Modules       #
# -*-*-*-*-*-*-*-*-*-*-* #

from google.auth.exceptions         import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials      import Credentials
from googleapiclient.discovery      import build
from email.message                  import EmailMessage
from email.mime.text                import MIMEText
from retry                          import retry



class GoogleAPI(object):
    def __init__(self, mk1):
        # MarkI
        self.mk1 = mk1     
    
        ## *-*-*-*-*-*-*-*- Initializing Attributes -*-*-*-*-*-*-*-* ##
        self.token_file_path = mk1.config.get("api_google","token_file_path") 
        self.token_method    = mk1.config.get("api_google","token_method") 
        self.token_format    = mk1.config.get("api_google","token_format") 
        
    
        ## *-*-*-*-*-*-*-*- Client Info -*-*-*-*-*-*-*-* ##
        self.credentials = self.get_credentials()
        self.auth_header = self.get_auth_header()
        
        
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #     Client & Exceptions    #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*#


    def get_credentials(self) : 
        
        try : 
            ## *-*-* 1. Loading token from '.json'  *-*-* ##
            
            if self.token_method == "secrets" : 
                token_file_path = os.environ['SECRETS_PATH'] + self.token_file_path
            else :
                token_file_path = self.token_file_path
                
            if self.token_format == "json" : 
                creds = Credentials.from_authorized_user_file(token_file_path)
                
            elif self.token_format == "pickle" : 
                with open(token_file_path, 'rb') as token:
                    creds = pickle.load(token)
            self.mk1.logging.logger.info("(GoogleAPI.get_credentials) Credentials Loaded.")
            

            # *-*-* 2. If there are no valid credentials available, let the user log in *-*-* ##
            if creds.valid :
                return creds
            
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self.mk1.logging.logger.info("(GoogleAPI.get_credentials) Token refreshed")
                return creds
            
            else : 
                # Token can't be refreshed
                self.mk1.logging.logger.error("(GoogleAPI.get_credentials) Token refresh failed")
                raise GoogleAuthError('Authentication failed for Google Sheets. Token refresh failed')

                    
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleAPI.get_credentials) Credentials loading failed : {e}")
            raise e
            
            

       
        
    """    
    def get_credentials_from_file(self, uSecret : bool = True):
        Retrieve or Generate the credentials of the OAuth 2.0 authentication process
        # Creating placeholders
        token_file_path = mk1.config.get("api_google","token_file_path")
    
        try:
            ## *-*-* 1. Loading pickled token *-*-* ##
            
            with open(token_file_path, 'rb') as token:
                creds = pickle.load(token)
                json_creds = json.loads(creds.to_json())
                with open(secrets_file, ‘w’) as f:
                     json.dump(json_creds, f)
                creds = Credentials.from_authorized_user_file(token_file)
                self.mk1.logging.logger.info("(GoogleAPI.get_credentials) Credentials Loaded.")
            
                    
            ## *-*-* 2. If there are no valid credentials available, let the user log in *-*-* ##
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    self.mk1.logging.logger.info("(GoogleAPI.get_credentials) Token refreshed")
                else:
                    # Token can't be refreshed
                    self.mk1.logging.logger.error("(GoogleAPI.get_credentials) Token refresh failed")
            return creds
                    
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleAPI.get_credentials) Token refresh failed : {e}")
            raise e
    """
            
        

    def get_auth_header(self):
        """Generate the headers of the OAuth 2.0 authentication process"""
        # Creating the placeholder
        headers = {}
        # Building the header (must be inserted in every request)
        self.credentials.apply(headers)
        return headers

    # Exceptions
    def request_check(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err_h:
            self.mk1.logging.logger.error(f"(GoogleAPI.request_check) Http Error: {err_h}")
            print(f"(GoogleAPI.request_check) Http Error: {err_h}")
            response = None
        except requests.exceptions.ConnectionError as err_c:
            self.mk1.logging.logger.error(f"(GoogleAPI.request_check) Connection Error: {err_c}")
            print(f"(GoogleAPI.request_check) Connection Error: {err_c}")
            response = None
        except requests.exceptions.Timeout as err_t:
            self.mk1.logging.logger.error(f"(GoogleAPI.request_check) Timeout Error: {err_t}")
            print(f"(GoogleAPI.request_check) Timeout Error: {err_t}")
            response = None
        except requests.exceptions.RequestException as err_r:
            self.mk1.logging.logger.error(f"(GoogleAPI.request_check) Request Error: {err_r}")
            print(f"(GoogleAPI.request_check) Request Error: {err_r}")
            response = None
        return response
    
# -------------------------------------- 1. (GOOGLE) SHEETS ----------------------------------------- #

class GoogleSheetsAPI(GoogleAPI):
    """
        API for using Google Sheets efficiently through python
        
        
        [SERVICE]
        1. `build_client`
         
        [UTILITIES]
        1. `df_to_list` - 
        2. `result_to_df`
        
        [GET]
        1. `get_df_from_tab` -
        2. `get_tab_num_dimension` - 
        3. `get_spreadsheet` - 
        
        [POST]
        1. `create_spreadsheet` - 
        2. `create_new_spreadsheet`  -
        3. `name_spreadsheet`  -
        4. `name_spreadsheet_tab`  -
        5. `write_df_to_tab` - 
    
    """
    def __init__(self, mk1):
        # Initializing GoogleAPI (Parent class)
        GoogleAPI.__init__(self, mk1)
        
    
        ## (A) Initializing Attributes
        # [google_sheets_api]
        self.service_name = mk1.config.get("api_google_sheets","service_name")
        self.version      = mk1.config.get("api_google_sheets","version")

        ## (B) Initializing Objects
        self.service = self.build_client()
        
        # Helper attribute to locate server-related-errors
        self.__server_err_codes = {500, 501, 503}
        
        
    # Service
    def build_client(self):
        try:
            # Creating the Sheets API client
            service = build(serviceName = self.service_name, 
                            version     = self.version, 
                            credentials = self.credentials,
                            cache_discovery = False)
            self.mk1.logging.logger.info("(GoogleSheetsAPI.build_client) Service build succeeded")
        except Exception as e:
            service = None
            self.mk1.logging.logger.error("(GoogleSheetsAPI.build_client) Service build failed: {}".format(e))
        return service
        
    
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #          UTILITIES             #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    
    def check_if_df_subset(
            self, 
            df_main : pd.DataFrame, 
            df      : pd.DataFrame 
        ) :
        
        df_tmp      = df.copy()
        df_main_tmp = df_main.copy()
        
        # 1. change column names
        
        df_tmp.columns = list(range(len(df_tmp.columns)))
        df_main_tmp.columns = list(range(len(df_main_tmp.columns)))
        
        # 2. convert to str & lower
        for c in df_tmp.columns : df_tmp[c] = df_tmp[c].astype(str).str.lower()
        for c in df_main_tmp.columns : df_main_tmp[c] = df_main_tmp[c].astype(str).str.lower()
        

        # 3. Merge the 2 dataframes
        
        df_merge = pd.concat([df_main_tmp, df_tmp], axis = 0)
        df_merge = df_merge.reset_index(drop = True)
        df_merge = df_merge.drop_duplicates(keep = "first")
        
        return len(df_merge) == len(df_main_tmp)

        
    
    # Formatter
    def df_to_list(
        self, 
        df          : pd.DataFrame, 
        has_index   : bool = True,
        has_headers : bool = True
    ) -> List:
        
        if has_index :
            index_name = df.index.name
            l = df.reset_index().values.tolist()
            
            if has_headers:
                l.insert(0, [index_name] + list(df.columns))
                
        else : 
            l = df.values.tolist()
            
            if has_headers:
                l.insert(0, list(df.columns))

        return l
    
    
    def result_to_df(
            self, 
            result      : Dict, 
            has_index   : bool = True,
            has_headers : bool = True,
            empty_value : str = ""
        ) -> pd.DataFrame:
        # headers
        if has_headers : 
            headers = result["values"].pop(0)
            df  = pd.DataFrame(result["values"], columns = headers)
            
        else : 
            df = pd.DataFrame(result["values"])
            
        # index
        if has_index : 
            df = df.set_index(df.iloc[:, 0].name)
            
        df = df.replace([''], [empty_value])        
        
        return df

    
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #          1/ GET requests       #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def get_df_from_tab(
            self, 
            spreadsheet_id          : str, 
            spreadsheet_range_name  : str , 
            spreadsheet_has_index   : bool = True, 
            spreadsheet_has_headers : bool = True, 
            spreadsheet_empty_value : str = ""
        ) -> pd.DataFrame : 
        
        """ Downloads specific Spreadsheet Tab as DataFrame
            
            :param: `spreadsheet_id`         : eg. '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
            :param: `spreadsheet_range_name` : eg. 'Class Data!A2:E'
            :param: `spreadsheet_index`      : True / False
            :param: `spreadsheet_empty_value`: None
            
        """
        
        # ------------------------------------------------------------ #
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{spreadsheet_range_name}"
        response = requests.get(url, headers = self.auth_header)
        result   = self.request_check(response)
        result   = json.loads(result.text)
        
        try : 
            df = self.result_to_df(result, spreadsheet_has_index, spreadsheet_has_headers)
        except KeyError as e : 
            df = pd.DataFrame()
            
            
        return df
    
    
    def get_tab_num_dimension(
            self,
            spreadsheet_id          : str, 
            spreadsheet_range_name  : str,
            dimension               : str = "ROWS"
        ) -> int:
        """Get the number of written rows of a specific tab"""
        
        url = "https://sheets.googleapis.com/v4/spreadsheets/{}/values/{}".format(spreadsheet_id, spreadsheet_range_name)
        response = requests.get(url, headers = self.auth_header)
        result   = self.request_check(response)
        result   = json.loads(result.text)
        
        
        if dimension == "ROWS" : 
            return len(result["values"])
        else : 
            return len(result["values"][0])
        
        


 
    def get_spreadsheet(self, spreadsheet_id : int) -> List[Dict]:
        """Get the whole the spreadsheet base on the spreadsheet id"""
        url = "https://sheets.googleapis.com/v4/spreadsheets/{}".format(spreadsheet_id)
        response = requests.get(url, headers = self.auth_header)
        result   = self.request_check(response) 
        return [{"spreadsheet_tab_index" : sheet["properties"]["index"], 
                 "spreadsheet_tab_gid"   : sheet["properties"]["sheetId"], 
                 "spreadsheet_tab_name"  : sheet["properties"]["title"]} for sheet in json.loads(result.text)["sheets"]]
    
    
    
    def get_tab_gid(self, 
                    spreadsheet_id       : str, 
                    spreadsheet_tab_name : str) -> int:
        """Get the `spreadsheet_gid` of a specific tab!"""
        spreadsheet_tab_gid = 0
        for tab in  self.get_spreadsheet(spreadsheet_id) :
            if tab["spreadsheet_tab_name"] == spreadsheet_tab_name : spreadsheet_tab_gid = tab["spreadsheet_tab_gid"]
                
        return spreadsheet_tab_gid
        
        

    def get_tab_url(self,
                    spreadsheet_id       : str, 
                    spreadsheet_tab_name : str) -> int:
        """Get the url (spreadsheet_id, spreadsheet_gid) of a specific tab!"""
        spreadsheet_tab_gid = self.get_tab_gid(spreadsheet_id,spreadsheet_tab_name )
        spreadsheet_tab_url = "https://docs.google.com/spreadsheets/d/{}/edit#gid={}".format(spreadsheet_id, spreadsheet_tab_gid)
        
        return spreadsheet_tab_url
        
    
    
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #    2/ POST requests (empty)    #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    
    def create_spreadsheet(self, 
                           spreadsheet_title    : str, 
                           spreadsheet_tab_name : str):
        
        ## 1. Creating the Google Sheet
        spreadsheet_dict = self.create_new_spreadsheet()
        time.sleep(2)
        
        ## 2. Naming Google Sheet Title Name
        self.name_spreadsheet(spreadsheet_id    = spreadsheet_dict["spreadsheet_id"],
                              spreadsheet_title = spreadsheet_title)
        time.sleep(2)
        
        ## 3. Naming Google Sheet Tab Name
        self.name_spreadsheet_tab(spreadsheet_id           = spreadsheet_dict["spreadsheet_id"], 
                                  spreadsheet_tab_name_old = "Sheet1",
                                  spreadsheet_tab_name_new = spreadsheet_tab_name)
        time.sleep(2)
        
        
        spreadsheet_dict["spreadsheet_title"] = spreadsheet_title
        return spreadsheet_dict
    

    def create_new_spreadsheet(self) -> Dict:
        url = "https://sheets.googleapis.com/v4/spreadsheets"
        response = requests.post(url, headers = self.auth_header)
        result   = self.request_check(response)
        return {"spreadsheet_id"    : json.loads(result.text)["spreadsheetId"], 
                "spreadsheet_title" : json.loads(result.text)["properties"]["title"],
                "spreadsheet_url"   : json.loads(result.text)["spreadsheetUrl"]}
    
    
    def create_spreadsheet_tab(self, 
                            spreadsheet_id       : str,
                            spreadsheet_tab_name : str) -> Dict:
        
        """Create a new tab at an existing spreadsheet """
        url  = "https://sheets.googleapis.com/v4/spreadsheets/{}:batchUpdate".format(spreadsheet_id)
        body = { "spreadsheetId" : spreadsheet_id,
                 "requests": 
                    {"addSheet": 
                          {"properties": { "title"   : spreadsheet_tab_name},
                          }
                     }
                }
        response = requests.post(url, headers = self.auth_header, data = json.dumps(body))
        result   = self.request_check(response) 
        return { "spreadsheet_id"       : spreadsheet_id,
                 "spreadsheet_tab_name" : spreadsheet_tab_name}
    
  
    def name_spreadsheet(self, 
                         spreadsheet_id    : str,
                         spreadsheet_title : str) -> Dict:
        # Creating the request body
        url = "https://sheets.googleapis.com/v4/spreadsheets/{}:batchUpdate".format(spreadsheet_id)
        body = {"requests": 
                    [{"updateSpreadsheetProperties": 
                        {"properties" : {"title"  : spreadsheet_title},
                         "fields"     : "*"
                        }
                     }]
               }

        response = requests.post(url, headers = self.auth_header, data = json.dumps(body))
        result   = self.request_check(response) 
        return {"spreadsheet_id"        : json.loads(result.text)["spreadsheetId"], 
                "spreadsheet_new_title" : spreadsheet_title}
    
    
    
    def name_spreadsheet_tab(self, 
                             spreadsheet_id           : str,
                             spreadsheet_tab_name_old : str,
                             spreadsheet_tab_name_new : str) -> Dict:
        
        spreadsheet_tab_gid = 0
        for tab in  self.get_spreadsheet(spreadsheet_id) : 
            if tab["spreadsheet_tab_name"] == spreadsheet_tab_name_old : spreadsheet_tab_gid = tab["spreadsheet_tab_gid"] 
        
        
        url  = "https://sheets.googleapis.com/v4/spreadsheets/{}:batchUpdate".format(spreadsheet_id)
        body = {"requests": 
                    [{"updateSheetProperties": 
                          {"properties": {"sheetId" : spreadsheet_tab_gid,
                                          "title"   : spreadsheet_tab_name_new},
                            "fields": "title"
                          }
                     }]
                }
        
        response = requests.post(url, headers = self.auth_header, data = json.dumps(body))
        result   = self.request_check(response) 
        return {"spreadsheet_tab_name_old" : spreadsheet_tab_name_old, 
                "spreadsheet_tab_name_new" : spreadsheet_tab_name_new}
    
    
    
    
    def insert_new_rows_or_columns(self,
                                   spreadsheet_id      : str,
                                   spreadsheet_tab_gid : int, 
                                   start_index         : int = 1,
                                   end_index           : int = 2,
                                   dimension           : str = "ROWS") : 
        
        
        #surl  = "https://sheets.googleapis.com/v4/spreadsheets/{}/values:batchUpdate".format(spreadsheet_id)
        
        body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId"    : str(spreadsheet_tab_gid),
                            "dimension"  : dimension,
                            "startIndex" : start_index,
                            "endIndex"   : end_index
                        },
                        "inheritFromBefore" : True
                    }
                }
            ]

        }
        
        result = self.service.spreadsheets().batchUpdate(spreadsheetId    = spreadsheet_id,
                                                         body             = body).execute()

        return result
    
    
    

    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #    2/ POST requests (not empty)    #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    
    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def clear_tab(
            self,
            spreadsheet_id          : str, 
            spreadsheet_range_name  : str
        ):

        body = {}
        result = self.service.spreadsheets().values().clear( 
            spreadsheetId = spreadsheet_id, 
            range          = spreadsheet_range_name,
            body           = body 
        ).execute()
        
        RESP_KEYS = {"spreadsheetId", "clearedRange"}
        # https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/clear
        # Naive check based on schema
        if set(result.keys()) != RESP_KEYS:
            # This both triggers @retry() and raises an error when we exhaust it
            raise requests.RequestException("Got 5XX error from Sheets API for clear_tab")

        print(result)
        
        print(result)
        return result
        
   
    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def write_df_to_tab(
            self, 
            df                      : pd.DataFrame, 
            spreadsheet_id          : str, 
            spreadsheet_range_name  : str,
            spreadsheet_has_index   : bool = True, 
            spreadsheet_has_headers : bool = True, 
            dimension               : str = "ROWS",
            value_input_option      : str = "USER_ENTERED" # RAW
        ) -> Dict:
        """ Ex: [[15], [10], [5]] (Column), [[15, 10, 5]] (Row), [[15, 10, 5], [25, 20, 15]] (2D Array) """
        
        url  = "https://sheets.googleapis.com/v4/spreadsheets/{}/values:batchUpdate".format(spreadsheet_id)
        body = {
            "valueInputOption": value_input_option,
            "data": [{
                "range"          : spreadsheet_range_name,
                "majorDimension" : dimension,
                "values"         : self.df_to_list(df, spreadsheet_has_index, spreadsheet_has_headers)
            }]
        } 
        
        response = requests.post(url, headers = self.auth_header, data = json.dumps(body))
        if response.status_code in self.__server_err_codes:
            # This both triggers @retry() and raises an error when we exhaust it
            raise requests.RequestException("Got 5XX error from Sheets API when writing data")

        result   = self.request_check(response)
        result   =  {
            "spreadsheet_id" : json.loads(result.text)["responses"][0]["spreadsheetId"], 
            "updated_range"  : json.loads(result.text)["responses"][0]["updatedRange"],
            "updated_cells"  : json.loads(result.text)["totalUpdatedCells"]
        }
        return result
    
    
    def append_rows_to_tab(
            self, 
            df                      : pd.DataFrame, 
            spreadsheet_id          : str, 
            spreadsheet_range_name  : str,
            append_if_not_exist     : bool = True,
            spreadsheet_has_index   : bool = True, 
            spreadsheet_has_headers : bool = True, 
            value_input_option      : str = "USER_ENTERED"
        ) -> Dict:
        
        if append_if_not_exist : 
        
            df_main = self.get_df_from_tab(
                spreadsheet_id, 
                spreadsheet_range_name, 
                spreadsheet_has_index,
                spreadsheet_has_headers
            ) 
            if self.check_if_df_subset(df_main, df) : return {}
        
 
        body = { 
            "majorDimension"  : "ROWS",
            "values"          : self.df_to_list(df, spreadsheet_has_index, spreadsheet_has_headers)
        }
        result = self.service.spreadsheets().values().append(
            spreadsheetId    = spreadsheet_id,
            range            = spreadsheet_range_name,
            valueInputOption = value_input_option,
            body             = body
        ).execute()

        return result
    
    
    
    def append_columns_to_tab(self, 
                              df                      : pd.DataFrame, 
                              spreadsheet_id          : str, 
                              spreadsheet_range_name  : str,
                              spreadsheet_has_index   : bool = False,
                              spreadsheet_has_headers : bool = False) : 
        
        
       
        
         
        ## 1. Find number of (rows,cols)
        num_cols = self.get_tab_num_dimension(spreadsheet_id, spreadsheet_range_name,"COLUMNS")
        num_rows = self.get_tab_num_dimension(spreadsheet_id, spreadsheet_range_name, "ROWS")
        
        
        
        
        ## 2. Insert new columns
        spreadsheet_tab_gid    = self.get_tab_gid(spreadsheet_id,spreadsheet_range_name)
        response = self.insert_new_rows_or_columns(spreadsheet_id, 
                                        str(spreadsheet_tab_gid), 
                                        start_index = num_cols, 
                                        end_index   = num_cols + df.shape[1], 
                                        dimension   =  "COLUMNS")
        
        
        ## 3. Write column
        spreadsheet_range_name = spreadsheet_range_name + f"!{str(chr(65 + num_cols))}1:{num_rows}"
        response = self.write_df_to_tab(df, spreadsheet_id, spreadsheet_range_name,  spreadsheet_has_index, spreadsheet_has_headers, "ROWS")
        return response
    
    
    
    
    
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #       3/ DELETE requests       #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    
    def delete_rows_or_columns(self, 
                               spreadsheet_id         : str, 
                               spreadsheet_range_name : str,
                               start_index            : int,
                               end_index              : int,
                               dimension              : str = "ROWS") : 
        
        spreadsheet_tab_gid = self.get_tab_gid(spreadsheet_id, spreadsheet_range_name)
        
        body = {
            "requests": [
                {
                    "deleteDimension": {
                        "range": {
                          "sheetId"    : spreadsheet_tab_gid,
                          "dimension"  : dimension,
                          "startIndex" : start_index,
                          "endIndex"   : end_index
                        }
                      }
                }
            ]

        }
        
        result = self.service.spreadsheets().batchUpdate(spreadsheetId    = spreadsheet_id,
                                                         body             = body).execute()

        return result
        
        
        
        
# -------------------------------------- 2. (GOOGLE) EMAIL ----------------------------------------- #



class GoogleEmailAPI(GoogleAPI):
    
    """
        API for using Google Email efficiently through python
         
        [non-API methods]
        1. `build_client` -
        2. `populate_body_message`
        3. `build_message`
        
        [GET]
        1. `get_css` -
        2. `get_email`-
        3. 
        
        [POST]
        1. `send_message`  - 
    
    """
    def __init__(self, mk1):
        # Initializing GoogleAPI (Parent class)
        GoogleAPI.__init__(self, mk1)
        
        ## (A) Initializing Attributes
        # [google mail api]
        self.service_name  = mk1.config.get("google_email_api","service_name")
        self.version       = mk1.config.get("google_email_api","version")
        self.my_email      = mk1.config.get("google_email_api","user_email")
        self.css_path      = mk1.config.get("google_email_api","css_path")
        self.email_path    = mk1.config.get("google_email_api","email_path")
        
        
        ## (B) Initializing Objects
        self.css_str   = self.get_css()
        self.email_str = self.get_email()
        self.service   = self.build_client()

    # Service
    def build_client(self):
        try:
            # Creating the Sheets API client
            service = build(serviceName = self.service_name, 
                            version     = self.version, 
                            credentials = self.credentials,
                            cache_discovery = False)
            self.mk1.logging.logger.info("(GoogleEmailAPI.build_client) Service build succeeded")
        except Exception as e:
            service = None
            self.mk1.logging.logger.error("(GoogleEmailAPI.build_client) Service build failed: {}".format(e))
        return service
    
    # CSS
    def get_css(self):

        with open(self.css_path, "r") as _file:
            css_str = _file.read().replace("\n", "").replace(" ", "")
        return css_str
    
    # Email Body
    def get_email(self):
        f = codecs.open(self.email_path, 'r')
        email_str = f.read()

        return email_str
    
    
    # Email population
    def populate_body_message(self, replace_dict) : 
        """Populating `body_html`"""
        body_html = self.email_str
        body_html = body_html.replace("{{css}}", self.css_str)
        
        
        try : 
        
            for key, value in replace_dict.items() : 
                body_html = body_html.replace("{{" + key + "}}",  str(value))
                
            self.mk1.logging.logger.info("(GoogleEmailAPI.populate_body_message) The body message was populated succcessfully")
                
        except Exception as e:
            self.mk1.logging.logger.error("(GoogleEmailAPI.populate_body_message) Message creation failed: {}".format(e))
            raise e
            
            
        self.body_html = body_html
    
        
        return body_html
        

    # Message/Email
    def build_message(self, email_from, email_to, email_subject):
        # Creating the "body_html"
        body_html = self.body_html

        try:
            # Composing an HTML message
            msg             = MIMEText(body_html, "html")
            msg["subject"]  = email_subject
            msg["from"]     = email_from
            msg["cc"]       = email_from
            msg["to"]       = email_to
        except Exception as e:
            self.mk1.logging.logger.error("(GoogleEmailAPI.build_message) Message creation failed: {}".format(e))
            raise e
            
        # Encoding message
        encoded_msg = base64.urlsafe_b64encode(bytes(msg))
        return  {'raw': str(encoded_msg).strip('b').strip('\'')}

  
    
    # Send
    def send_message(self, email_from, email_to, email_subject ):

        # Building the message
        msg = self.build_message(email_from, email_to, email_subject)

        # Sending the email
        try : 
            send = self.service.users().messages().send(userId = self.my_email, body = msg).execute()
            self.mk1.logging.logger.info("(GoogleEmailAPI.send_message) Message sent.")
        except Exception as e: 
            self.mk1.logging.logger.error("(GoogleEmailAPI.send_message) Message sending failed: {}".format(e))
            raise e

        return send

    
# -------------------------------------- 3. (GOOGLE) DRIVE ----------------------------------------- #




class GoogleDriveAPI(GoogleAPI):
    """
        https://developers.google.com/drive/api/v3/reference
        
        API for using Google Drive efficiently through python
         
        [non-API methods]
        1. `build_client` -
        2. `mime_to_str`
        3. `str_to_mime`
        4. `datetime_to_ISO8601`
        5. `build_query`
        
        
        [GET]
        1. `get_file` -
        
        [POST]
        1. `copy_file`  - 
        
        [UPDATE]
        1. `update_file`  - 
        
    """
    def __init__(self, mk1):
        # Initializing GoogleAPI (parent class)
        GoogleAPI.__init__(self, mk1)
        
        
        ## (A) Initializing Attributes
        # [google drive api]
        self.service_name  = mk1.parser.get("google_drive_api","service_name")
        self.version       = mk1.parser.get("google_drive_api","version")
        
        
        ## (B) Initializing Objects
        self.service = self.build_client()
        
        
    # Service
    def build_client(self):
        try:
            # Creating the Google Drive API client
            service = build(serviceName = self.service_name, 
                            version     = self.version, 
                            credentials = self.credentials)
            self.mk1.logging.logger.info("(GoogleDriveAPI.build_client) Service build succeeded")
        except Exception as e:
            service = None
            self.mk1.logging.logger.error("(GoogleDriveAPI.build_client) Service build failed: {}".format(e))
        return service
 
    
    # MIME Types
    def mime_to_str(self, 
                    mime_type : str = "application/vnd.google-apps.document") -> str:
        # Creating the placeholder
        mime_str = None
        # Finding the right MIMEType (more types on the execution cell)
        if mime_type == "application/vnd.google-apps.document":
            mime_str = "google_doc"
        elif mime_type == "application/vnd.google-apps.drawing":
            mime_str = "google_drawing"
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            mime_str = "google_sheets"
        elif mime_type == "application/vnd.google-apps.presentation":
            mime_str = "google_slides"
        elif mime_type == "application/vnd.google-apps.form":
            mime_str = "google_form"
        elif mime_type == "application/vnd.google-apps.file":
            mime_str = "drive_file"
        elif mime_type == "application/vnd.google-apps.folder":
            mime_str = "drive_folder"
        elif mime_type == "application/vnd.google-apps.script":
            mime_str = "apps_script"
        else:
            mime_str = "unknown"
        return mime_str
    
    def str_to_mime(self, mime_str : str) -> str:
        # Creating the placeholder
        mime_type = None
        # Finding the right string (more types on the execution cell)
        if mime_str == "google_doc":
            mime_type = "application/vnd.google-apps.document"
        elif mime_str == "google_drawing":
            mime_type = "application/vnd.google-apps.drawing"
        elif mime_str == "google_sheets":
            mime_type = "application/vnd.google-apps.spreadsheet"
        elif mime_str == "google_slides":
            mime_type = "application/vnd.google-apps.presentation"
        elif mime_str == "google_form":
            mime_type = "application/vnd.google-apps.form"
        elif mime_str == "drive_file":
            mime_type = "application/vnd.google-apps.file"
        elif mime_str == "drive_folder":
            mime_type = "application/vnd.google-apps.folder"
        elif mime_str == "apps_script":
            mime_type = "application/vnd.google-apps.script"
        else:
            mime_type = "unknown"
        return mime_type
    
    # Datetime
    def datetime_to_ISO8601(self, datetime_obj):
        return datetime_obj.strftime("%Y-%m-%d %H:%M:%S") 
    
    # Query
    def build_query(self, 
                    folder_id : int, 
                    name      : str = None, 
                    trashed   : str = False, 
                    mime      : str = None) -> str:
        try:
            # Creating the query placeholders 
            query = "'{}' in parents and trashed={}".format(folder_id, str(trashed).lower())
            
            # Adding constraints to "query"
            if name is not None: query += " and name contains '{}'".format(name)
            if mime is not None: query += " and mimeType='{}'".format(self.str_to_mime(mime))
                
            self.mk1.logging.logger.info("(GoogleDriveAPI.build_query) Query placeholders succeeded")
        except: 
            self.mk1.logging.logger.error("(GoogleDriveAPI.build_query) Query placeholders failed: {}".format(e))
            raise e
        return query
    
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #          1/ GET requests       #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    
    def get_file(self, 
                 file_id : int, 
                 fields  : str = "id,name,mimeType") -> Dict:
        # Creating the request body
        url = "https://www.googleapis.com/drive/v3/files/{}?fields={}".format(file_id, fields)
        # Requesting
        
        try : 
        
            response = requests.get(url, headers = self.auth_header)
            result   = self.request_check(response)
            self.mk1.logging.logger.info("(GoogleDriveAPI.get_file) Getting file succeeded")
        
        except: 
            self.mk1.logging.logger.error("(GoogleDriveAPI.get_file) Getting file failed: {}".format(e))
            raise e
            
        return {"file_id"   : json.loads(result.text)["id"], 
                "file_name" : json.loads(result.text)["name"],
                "file_type" : self.mime_to_str(json.loads(result.text)["mimeType"])} 
        
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #          3/ POST requests      #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    def copy_file(self, 
                  file_id       : int, 
                  parent_folder : str) -> Dict:
        # Creating the request body
        url  = "https://www.googleapis.com/drive/v3/files/{}/copy".format(file_id)
        body = {"kind"     : "drive#file",
                "parents"  : [parent_folder],
                "mimeType" : "application/vnd.google-apps.spreadsheet"}
        # Requesting
        try : 
        
            response = requests.post(url, headers = self.auth_header, data = json.dumps(body))
            result   = self.request_check(response)
            self.mk1.logging.logger.info("(GoogleDriveAPI.copy_file) Copying file succeeded")
        
        except: 
            self.mk1.logging.logger.error("(GoogleDriveAPI.copy_file) Copying file  failed: {}".format(e))
            raise e
            
            
        return {"copy_id"  : json.loads(result.text)["id"], 
                "copy_name": json.loads(result.text)["name"],
                "copy_type": self.mime_to_str(json.loads(result.text)["mimeType"])} 
    
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #          4/ UPDATE requests    #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    
    def update_file(self, 
                    file_id   : int, 
                    new_name  : str = None, 
                    add_parent    = None, 
                    remove_parent = None) -> Dict:
        # PS: Updates name and/or location (client version)
        # Creating the request body
        
        _body = {"name": new_name} 
        
        # Requesting
        try : 
            result = self.service.files().update(fileId        = file_id, 
                                                 addParents    = add_parent, 
                                                 removeParents = remove_parent, 
                                                 body          = _body).execute()
            self.mk1.logging.logger.info("(GoogleDriveAPI.update_file) Updating file succeeded")
        
        except: 
            self.mk1.logging.logger.error("(GoogleDriveAPI.update_file) Updating file  failed: {}".format(e))
            raise e
            
        return {"update_id"   : result.get("id"), 
                "update_name" : result.get("name"),
                "update_type" : self.mime_to_str(result.get("mimeType"))} 
    
    