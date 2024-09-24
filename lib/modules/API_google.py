# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    [*] Description : Py3 wrapper for Google API
    [*] Author      : dgeorgiou3@gmail.com
    [*] Date        : Sep, 2023
    [*] Links       :
    [*] Google APIs supported so far :
        - Google Sheets API
        - Google Drive API
        - Google Email API
"""

# -*-*-*-*-*-*-*-*-*-*-* #
#     Basic Modules      #
# -*-*-*-*-*-*-*-*-*-*-* #
import requests, pickle, os, json, yaml, time, codecs, base64, sys
import urllib.parse
import pandas as pd
import numpy as np
from bs4      import BeautifulSoup
from base64   import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from typing  import (
    Callable, Dict, Generic, Optional, Set, Tuple, TypeVar, Deque, List, Any, Union
)


# -*-*-*-*-*-*-*-*-*-*-**-*-*-* #
#      Third-Party Modules      #
# -*-*-*-*-*-*-*-*-*-*-**-*-*-* #
import webbrowser
import subprocess
import psutil
import socket
from retry            import retry
from urllib.parse     import urlencode
from urllib.parse     import quote as uquote
## Google  API
from google.auth.exceptions         import GoogleAuthError
from google_auth_oauthlib.flow 		import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials      import Credentials
from googleapiclient.discovery      import build
## Google Email API
from email.message                  import EmailMessage
from email.mime.text                import MIMEText
## Google Drive API
from googleapiclient.http           import MediaFileUpload


class GoogleAPI(object):
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/documents'
    ]
    def __init__(self, mk1):
        self.mk1 = mk1
        ## *-*-*-*-*-*-*-*- Configuration (attributes) -*-*-*-*-*-*-*-* ##
        self.token_saved_desination = self.mk1.config.get("api_google","token_saved_desination") # local, secrets
        self.token_file_path        = self.mk1.config.get("api_google","token_file_path")
        self.token_format           = self.mk1.config.get("api_google","token_format")
        self.token_file_path        = self.get_token_file_path()    # parse accurate token path

        ## *-*-*-*-*-*-*-*- Client Info -*-*-*-*-*-*-*-* #
        #self.credentials = self.oauth_with_refresh()
        self.credentials = self.oauth(force = False)
        self.auth_header = self.get_auth_header()


    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*#
    #     Client & Exceptions    #
    #-*-*-*-*-*-*-*-*-*-*-*-*-*-*#

    def oauth_with_refresh(self) :
        """
            TODO
            ----
            * Set force back to False. Fore some reason ieven if we check the attributes `valid`, `expired`, `expired`, `refresh_token`
              and everything looks ok, the token is not valid anymore abd we need to force the refreshing.
        """
        credentials = self.oauth(force = False)

        if credentials.valid :
            return credentials

        elif credentials and credentials.expired and credentials.refresh_token:
            credentials = self.oauth(force = True)
            return credentials


    def oauth(self, force : bool = False):
        credentials_info = self.get_credentials_info()
        credentials_info = self.authorize_user(credentials_info, force = force)
        self.save_credentials_info(credentials_info)
        credentials = self.get_credentials(credentials_info)
        return credentials


    def open_in_chrome(self, url):
        try:
            # macOS command to open a URL in Chrome
            subprocess.run(['open', '-a', 'Google Chrome', url])
        except Exception as e:
            print(f"Failed to open in Chrome: {e}")


    def get_token_file_path(self) :
        token_file_path = self.token_file_path
        if self.token_saved_desination == "secrets" :  # local, secrets
            token_file_path = os.environ['SECRETS_PATH'] + token_file_path
        return token_file_path

    def free_up_port(self, port):
        """
            Try to free up the specified port by killing the process using the port.

            Args
            ----
                :param: port (int): Port number to be freed up.
                :returns: bool: True if the port was successfully freed up, False otherwise.
        """
        print(f" --------- Port : {port}")
        try:
            # Check if the port is in use
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                s.listen(1)

        except OSError:
            try:
                # Try to find the process using the port and kill it
                process_info = subprocess.run(['sudo', 'lsof', '-ti', f':{port}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                #process_ids = [line.split()[1] for line in process_info.stdout.splitlines()[1:]]
                process_ids = process_info.stdout.splitlines()
                for pid in process_ids:
                    print(pid)
                    subprocess.run(['sudo', 'kill', '-9', str(pid)])
                    time.sleep(1)
                return True
            except subprocess.CalledProcessError:
                print(f"Unable to free up port {port}.")

        return False

    def authorize_user(
            self,
            credentials_info,
            app   : str = "web",
            force : bool = False
        ) -> None:
        """
            Authentication and Authorization is between the client (user) and Google Accounts.
            Your software is not involved in the credentials part (username, password, etc.).
            The user must grant permission to Google Accounts to allow your services to access the user's Google Identity.

            1. Read the `.json` file
               - If `refresh_token` exists return
               - Else
               2.1 Set up the OAuth2 flow
               2.2 Run the OAuth2 flow and authorize the user
               2.3 Add the refresh token
               2.4 Save the updated JSON back to the file

        """

        try :
            if "refresh_token" in credentials_info[app] and not force :
                return credentials_info

            redirect_uri = credentials_info[app]['redirect_uris'][0]
            port = int(redirect_uri.split(":")[-1].split("/")[0])
            flow = InstalledAppFlow.from_client_secrets_file(
                self.token_file_path,
                scopes = self.SCOPES,
            )
            self.free_up_port(port)
            credentials = flow.run_local_server(
                port                   = port,
                access_type            = 'offline',      # Enable offline access so that you can refresh an access token without re-prompting the user for permission. Recommended for web server apps.
                open_browser           = True,
                include_granted_scopes = 'true' # Enable incremental authorization. Recommended as a best practice.
            )
            #print(credentials.token, credentials.refresh_token)
            credentials_info[app]["refresh_token"] = credentials.refresh_token #credentials.token # TODO  : change back to refresh token
            self.mk1.logging.logger.info(f"(GoogleAPI.authorizate_user) User authorization for uri {redirect_uri} was successful")
            return credentials_info

        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleAPI.authorizate_user)  User authorization for uri {redirect_uri} failed : {e}")
            raise e

    def get_credentials_info(self) :
        with open(self.token_file_path, 'rb') as file:
            credentials_info = json.load(file)
        return credentials_info

    def save_credentials_info(self, credentials_info):
        with open(self.token_file_path, 'w') as file:
            json.dump(credentials_info, file)


    def get_credentials(self, credentials_info, app : str = "web") :
        try :
            if self.token_format == "json" :
                #credentials = Credentials.from_authorized_user_info(credentials_info[app])
                credentials = Credentials(
                    credentials_info[app]["refresh_token"],
                    refresh_token = credentials_info[app]["refresh_token"],
                    token_uri     = credentials_info[app]["token_uri"],
                    client_id     = credentials_info[app]["client_id"],
                    client_secret = credentials_info[app]["client_secret"],
                    scopes        = self.SCOPES
                )

            elif self.token_format == "pickle" :
                with open(self.token_file_path, 'rb') as file:
                    credentials = pickle.load(file)

            self.mk1.logging.logger.info("(GoogleAPI.get_credentials) Credentials Loaded.")
            return credentials

        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleAPI.get_credentials) Credentials loading failed : {e}")
            raise e

    # def refresh_credentials(self, credentials):
    #     try:
    #         if credentials.valid :
    #             return credentials

    #         elif credentials and credentials.expired and credentials.refresh_token:
    #             credentials.refresh(Request())
    #             self.mk1.logging.logger.info("(GoogleAPI.refresh_credentials) Token refreshed")
    #             return credentials

    #         # elif self.token_format == "json" :
    #         #     credentials_info = self.authorize_user(force = True)
    #         #     credentials = self.get_credentials(credentials_info)
    #         #     self.mk1.logging.logger.info("(GoogleAPI.refresh_credentials) Token refreshed")
    #         #     return credentials

    #         else :
    #             # Token can't be refreshed
    #             self.mk1.logging.logger.error("(GoogleAPI.refresh_credentials) Token refresh failed")
    #             raise GoogleAuthError('Authentication failed for Google Sheets. Token refresh failed')

    #     except Exception as e:
    #         self.mk1.logging.logger.error(f"(GoogleAPI.refresh_credentials) Credentials loading failed : {e}")
    #         raise e

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
    API for using Google Sheets efficiently through Python.

    [SERVICE]
        1. `build_client`

    [UTILITIES]
        1. `df_to_list`
        2. `result_to_df`

    [GET]
        1. `get_df_from_tab`
        2. `get_tab_num_dimension`
        3. `get_spreadsheet`

    [POST]
        1. `create_spreadsheet`
        2. `create_new_spreadsheet`
        3. `name_spreadsheet`
        4. `name_spreadsheet_tab`
        5. `write_df_to_tab`
    """

    def __init__(self, mk1, google_api):
        self.mk1 = mk1

        self.__server_err_codes = {500, 501, 503}
        self.__resp_keys        = {"spreadsheetId", "clearedRange"}
        self.__null_values      =  [None, np.nan, "", "#N/A", "null", "nan", "NaN"]

        ## __________ *** Initializing (attributes) *** __________
        self.service_name = mk1.config.get("api_google_sheets","service_name")
        self.version      = mk1.config.get("api_google_sheets","version")
        self.credentials  = google_api.credentials
        self.auth_header  = google_api.auth_header

        ## __________ *** Initializing (client) *** __________
        self.service = self.build_client()

    def build_client(self):
        try:
            service = build(
                serviceName=self.service_name,
                version=self.version,
                credentials=self.credentials,
                cache_discovery=False
            )
            self.mk1.logging.logger.info("(GoogleSheetsAPI.build_client) Service build succeeded")
            return service
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.build_client) Service build failed: {e}")
            return None

    # Utilities
    def quote(self, value, safe="", encoding="utf-8"):
        return uquote(value.encode(encoding), safe)

    def check_if_df_subset(self, df_main: pd.DataFrame, df: pd.DataFrame) -> bool:
        try:
            df_tmp = df.copy()
            df_main_tmp = df_main.copy()

            df_tmp.columns = range(len(df_tmp.columns))
            df_main_tmp.columns = range(len(df_main_tmp.columns))

            df_tmp = df_tmp.astype(str).apply(lambda x: x.str.lower())
            df_main_tmp = df_main_tmp.astype(str).apply(lambda x: x.str.lower())

            df_merge = pd.concat([df_main_tmp, df_tmp]).drop_duplicates(keep="first").reset_index(drop=True)
            result = len(df_merge) == len(df_main_tmp)
            self.mk1.logging.logger.info("(GoogleSheetsAPI.check_if_df_subset) Subset check successful")
            return result
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.check_if_df_subset) Subset check failed: {e}")
            return False

    def df_to_list(self, df: pd.DataFrame, has_index: bool = True, has_headers: bool = True) -> List:
        try:
            if has_index:
                index_name = df.index.name
                l = df.reset_index().values.tolist()
                if has_headers:
                    l.insert(0, [index_name] + list(df.columns))
            else:
                l = df.values.tolist()
                if has_headers:
                    l.insert(0, list(df.columns))

            l = [[
                "" if item in self.__null_values or (isinstance(item, float) and np.isnan(item)) else item
                for item in sublist
            ] for sublist in l]
            self.mk1.logging.logger.info("(GoogleSheetsAPI.df_to_list) DataFrame converted to list successfully")
            return l
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.df_to_list) Conversion failed: {e}")
            return []

    def result_to_df(self, result: Dict, has_index: bool = True, has_headers: bool = True, empty_value: str = "") -> pd.DataFrame:
        try:
            if has_headers:
                headers = result["values"].pop(0)
                df = pd.DataFrame(result["values"], columns=headers)
            else:
                df = pd.DataFrame(result["values"])

            if has_index:
                df = df.set_index(df.columns[0])
            df = df.replace([''], [empty_value])
            self.mk1.logging.logger.info("(GoogleSheetsAPI.result_to_df) Result converted to DataFrame successfully")
            return df
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.result_to_df) Conversion failed: {e}")
            return pd.DataFrame()

    # GET requests
    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def get_df_from_tab(self, spreadsheet_id: str, spreadsheet_range_name: str, spreadsheet_has_index: bool = True, spreadsheet_has_headers: bool = True, spreadsheet_empty_value: str = "") -> pd.DataFrame:
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=spreadsheet_range_name
            ).execute()

            if not result:
                self.mk1.logging.logger.info("(GoogleSheetsAPI.get_df_from_tab) No data found.")
                return pd.DataFrame()

            df = self.result_to_df(
                result=result,
                has_index=spreadsheet_has_index,
                has_headers=spreadsheet_has_headers
            )
            self.mk1.logging.logger.info(f"(GoogleSheetsAPI.get_df_from_tab) Data loaded. Shape = {df.shape}")
            return df
        except KeyError as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.get_df_from_tab) Data loading failed, error: {e}")
            return pd.DataFrame()

    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def get_tab_num_dimension(self, spreadsheet_id: str, spreadsheet_range_name: str, dimension: str = "ROWS") -> int:
        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{spreadsheet_range_name}"
            response = requests.get(url, headers=self.auth_header)
            self.request_check(response)
            result = response.json()
            num_dim = len(result["values"]) if dimension == "ROWS" else len(result["values"][0])
            self.mk1.logging.logger.info(f"(GoogleSheetsAPI.get_tab_num_dimension) Number of {dimension} = {num_dim}")
            return num_dim
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.get_tab_num_dimension) Failed to get dimension: {e}")
            return 0

    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def get_spreadsheet(self, spreadsheet_id: str) -> List[Dict]:
        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
            response = requests.get(url, headers=self.auth_header)
            self.request_check(response)
            result = response.json()
            spreadsheet_info = [{
                "spreadsheet_tab_index": sheet["properties"]["index"],
                "spreadsheet_tab_gid": sheet["properties"]["sheetId"],
                "spreadsheet_tab_name": sheet["properties"]["title"]
            } for sheet in result["sheets"]]
            self.mk1.logging.logger.info(f"(GoogleSheetsAPI.get_spreadsheet) Retrieved spreadsheet info successfully")
            return spreadsheet_info
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.get_spreadsheet) Failed to retrieve spreadsheet info: {e}")
            return []

    def get_tab_gid(self, spreadsheet_id: str, spreadsheet_tab_name: str) -> int:
        try:
            for tab in self.get_spreadsheet(spreadsheet_id):
                if tab["spreadsheet_tab_name"] == spreadsheet_tab_name:
                    self.mk1.logging.logger.info(f"(GoogleSheetsAPI.get_tab_gid) Found GID for tab {spreadsheet_tab_name}: {tab['spreadsheet_tab_gid']}")
                    return tab["spreadsheet_tab_gid"]
            self.mk1.logging.logger.info(f"(GoogleSheetsAPI.get_tab_gid) Tab {spreadsheet_tab_name} not found")
            return 0
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.get_tab_gid) Failed to get tab GID: {e}")
            return 0

    def get_tab_url(self, spreadsheet_id: str, spreadsheet_tab_name: str) -> str:
        try:
            spreadsheet_tab_gid = self.get_tab_gid(spreadsheet_id, spreadsheet_tab_name)
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={spreadsheet_tab_gid}"
            self.mk1.logging.logger.info(f"(GoogleSheetsAPI.get_tab_url) URL for tab {spreadsheet_tab_name}: {url}")
            return url
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.get_tab_url) Failed to get tab URL: {e}")
            return ""

    # POST requests
    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def create_spreadsheet(self, title: str, sheets: List[Dict] = [], fields: List[str] = []) -> str:
        try:
            url = "https://sheets.googleapis.com/v4/spreadsheets"
            data = {
                "properties": {"title": title},
                "sheets": sheets
            }
            response = requests.post(url, headers=self.auth_header, json=data)
            self.request_check(response)
            result = response.json()
            spreadsheet_id = result["spreadsheetId"]
            self.mk1.logging.logger.info(f"(GoogleSheetsAPI.create_spreadsheet) Spreadsheet created with ID: {spreadsheet_id}")
            return spreadsheet_id
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.create_spreadsheet) Failed to create spreadsheet: {e}")
            return ""

    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def create_new_spreadsheet(self, title: str) -> str:
        return self.create_spreadsheet(title=title)

    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def name_spreadsheet(self, spreadsheet_id: str, title: str) -> bool:
        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
            data = {"properties": {"title": title}}
            response = requests.put(url, headers=self.auth_header, json=data)
            self.request_check(response)
            self.mk1.logging.logger.info(f"(GoogleSheetsAPI.name_spreadsheet) Renamed spreadsheet to {title}")
            return True
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.name_spreadsheet) Failed to rename spreadsheet: {e}")
            return False

    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def name_spreadsheet_tab(self, spreadsheet_id: str, spreadsheet_tab_name: str, new_tab_name: str) -> bool:
        try:
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/batchUpdate"
            data = {
                "requests": [{
                    "updateSheetProperties": {
                        "properties": {"sheetId": self.get_tab_gid(spreadsheet_id, spreadsheet_tab_name), "title": new_tab_name},
                        "fields": "title"
                    }
                }]
            }
            response = requests.post(url, headers=self.auth_header, json=data)
            self.request_check(response)
            self.mk1.logging.logger.info(f"(GoogleSheetsAPI.name_spreadsheet_tab) Renamed tab {spreadsheet_tab_name} to {new_tab_name}")
            return True
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleSheetsAPI.name_spreadsheet_tab) Failed to rename tab: {e}")
            return False

    @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    def write_df_to_tab(
            self,
            df                      : pd.DataFrame,
            spreadsheet_id          : str,
            spreadsheet_range_name  : str,
            spreadsheet_has_index   : bool = False,
            spreadsheet_has_headers : bool = True,
            dimension               : str = "ROWS",
            value_input_option      : str = "USER_ENTERED" # RAW
        ) -> Dict:
        """

            Args
            ----
                :param: df - The dataftame that need to be translated into list
                :var: values - The transformed dataframe
                     - Example : [[15], [10], [5]] (Column), [[15, 10, 5]] (Row), [[15, 10, 5], [25, 20, 15]] (2D Array)

        """
        url  = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate"

        ## *-*-*-*-*-*-*-*-*-*-*-*-*-*- Preparing the request body -*-*-*-*-*-*-*-*-*-*-*-*-*-* ##
        values =  self.df_to_list(
            df          = df,
            has_index   = spreadsheet_has_index,
            has_headers = spreadsheet_has_headers
        )
        body = {
            "valueInputOption": value_input_option,
            "data": [{
                "range"          : spreadsheet_range_name,
                "majorDimension" : dimension,
                "values"         : values
            }]
        }

        ## *-*-*-*-*-*-*-*-*-*-*-*-*-*- Requesting -*-*-*-*-*-*-*-*-*-*-*-*-*-* ##
        response = requests.post(
            url     = url,
            headers = self.auth_header,
            data    = json.dumps(body)
        )

        ## *-*-*-*-*-*-*-*-*-*-*-*-*-*- Processing the response -*-*-*-*-*-*-*-*-*-*-*-*-*-* ##
        if response.status_code in self.__server_err_codes:
            # This both triggers @retry() and raises an error when we exhaust it
            raise requests.RequestException("Got 5XX error from Sheets API when writing data")
        response = self.request_check(response)
        result = json.loads(response.text)
        result =  {
            "spreadsheet_id" : result["responses"][0]["spreadsheetId"],
            "updated_range"  : result["responses"][0]["updatedRange"],
            "updated_cells"  : result["totalUpdatedCells"]
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
        """

            Args
            ----
                :param: df - The dataftame that need to be translated into list
                :var: values - The transformed dataframe
                     - Example : [[15], [10], [5]] (Column), [[15, 10, 5]] (Row), [[15, 10, 5], [25, 20, 15]] (2D Array)

            Notes
            -----
            * Do not put the valueInputOption inside the body as in write_df !!
            * spreadsheet_range_name = urllib.parse.quote(spreadsheet_range_name)

            url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{spreadsheet_range_name}:append?valueInputOption={value_input_option}"
            response = requests.post(
                url     = url,
                headers = self.auth_header,
                data    = json.dumps(body)
            )
            if response.status_code in self.__server_err_codes:
                # This both triggers @retry() and raises an error when we exhaust it
                raise requests.RequestException("Got 5XX error from Sheets API when writing data")
            response = self.request_check(response)
        """
        ## *-*-*-*-*-*-*-*-*-*-*-*-*-*- Preparing the request body -*-*-*-*-*-*-*-*-*-*-*-*-*-* ##
        values =  self.df_to_list(
            df          = df,
            has_index   = spreadsheet_has_index,
            has_headers = spreadsheet_has_headers
        )
        body = {
            "majorDimension"   : "ROWS",
            "values"           : values
        }

        ## *-*-*-*-*-*-*-*-*-*-*-*-*-*- Requesting ...  -*-*-*-*-*-*-*-*-*-*-*-*-*-* ##
        response = self.service.spreadsheets().values().append(
            spreadsheetId    = spreadsheet_id,
            range            = spreadsheet_range_name,
            valueInputOption = value_input_option,
            body             = body
        ).execute()

        ## *-*-*-*-*-*-*-*-*-*-*-*-*-*- Processing the response -*-*-*-*-*-*-*-*-*-*-*-*-*-* ##
        if 'updates' in response:
            updated_range = response['updates'].get('updatedRange', 'Unknown range')
            updated_rows = response['updates'].get('updatedRows', 0)
            self.mk1.logging.logger.info(f"Updated range: {updated_range}, Rows updated: {updated_rows}")
        else:
            self.mk1.logging.logger.warning("No 'updates' field in response.")

        return



    def append_columns_to_tab(
            self,
            df                      : pd.DataFrame,
            spreadsheet_id          : str,
            spreadsheet_range_name  : str,
            spreadsheet_has_index   : bool = False,
            spreadsheet_has_headers : bool = False
        ) :
        """ WIP """

        ## ------- 1. Find number of (rows,cols)
        num_cols = self.get_tab_num_dimension(spreadsheet_id, spreadsheet_range_name,"COLUMNS")
        num_rows = self.get_tab_num_dimension(spreadsheet_id, spreadsheet_range_name, "ROWS")


        ## ------ 2. Insert new columns
        spreadsheet_tab_gid = self.get_tab_gid(spreadsheet_id,spreadsheet_range_name)
        response = self.insert_new_rows_or_columns(
            spreadsheet_id      = spreadsheet_id,
            spreadsheet_tab_gid = str(spreadsheet_tab_gid),
            start_index         = num_cols,
            end_index           = num_cols + df.shape[1],
            dimension           =  "COLUMNS"
        )


        ## ----- 3. Write column
        spreadsheet_range_name = spreadsheet_range_name + f"!{str(chr(65 + num_cols))}1:{num_rows}"
        response = self.write_df_to_tab(
            df                      = df,
            spreadsheet_id          = spreadsheet_id,
            spreadsheet_range_name  = spreadsheet_range_name,
            spreadsheet_has_index   = spreadsheet_has_index,
            spreadsheet_has_headers = spreadsheet_has_headers,
            dimension               = "ROWS"
        )
        return response

    # @retry(exceptions=requests.RequestException, tries=10, delay=2, jitter=(0, 2))
    # def write_df_to_tab(self, df: pd.DataFrame, spreadsheet_id: str, spreadsheet_tab_name: str, has_index: bool = True, has_headers: bool = True) -> bool:
    #     try:
    #         url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{spreadsheet_tab_name}:append"            
    #         data = {
    #             "range": spreadsheet_tab_name,
    #             "values": self.df_to_list(df, has_index, has_headers)
    #         }
    #         response = requests.post(url, headers=self.auth_header, json=data)
    #         self.request_check(response)
    #         self.mk1.logging.logger.info(f"(GoogleSheetsAPI.write_df_to_tab) Data written to tab {spreadsheet_tab_name} successfully")
    #         return True
    #     except Exception as e:
    #         raise e
    #         self.mk1.logging.logger.error(f"(GoogleSheetsAPI.write_df_to_tab) Failed to write data to tab: {e}")
    #         return False


# -------------------------------------- 2. (GOOGLE) EMAIL ----------------------------------------- #
class GoogleEmailAPI(GoogleAPI):
    """
    API for using Google Email efficiently through Python.

    [non-API methods]
        1. `build_client` -
        2. `populate_body_message`
        3. `build_message`

    [GET]
        1. `get_css` -
        2. `get_email`-
        3. `get_emails_from_past_days` -
        4. `get_emails_with_keywords` -
        5. `get_email_text_info` -

    [POST]
        1. `send_message`  -
    """

    def __init__(self, mk1, google_api):
        self.mk1 = mk1

        ## __________ *** Initializing (attributes) *** __________
        self.service_name = mk1.config.get("api_google_email","service_name")
        self.version      = mk1.config.get("api_google_email","version")
        self.credentials  = google_api.credentials
        self.auth_header  = google_api.auth_header

        ## __________ *** Initializing (client) *** __________
        self.service = self.build_client()


    
    def __init__(self, mk1, google_api):
        self.mk1 = mk1
        self.service_name = mk1.config.get("api_google_email", "service_name")
        self.version = mk1.config.get("api_google_email", "version")
        self.credentials = google_api.credentials
        self.auth_header = google_api.auth_header
        self.service = self.build_client()

    def build_client(self):
        try:
            service = build(
                serviceName=self.service_name,
                version=self.version,
                credentials=self.credentials,
                cache_discovery=False
            )
            self.mk1.logging.logger.info("(GoogleEmailAPI.build_client) Service build succeeded")
            return service
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.build_client) Service build failed: {e}")
            return None

    # CSS
    def get_css(self) -> str:
        try:
            with open(self.css_path, "r") as _file:
                css_str = _file.read().replace("\n", "").replace(" ", "")
            self.mk1.logging.logger.info("(GoogleEmailAPI.get_css) CSS loaded successfully")
            return css_str
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.get_css) Failed to load CSS: {e}")
            return ""

    # Email Body
    def get_email(self) -> str:
        try:
            with codecs.open(self.email_path, 'r') as f:
                email_str = f.read()
            self.mk1.logging.logger.info("(GoogleEmailAPI.get_email) Email template loaded successfully")
            return email_str
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.get_email) Failed to load email template: {e}")
            return ""

    def populate_body_message(self, replace_dict: Dict[str, str]) -> str:
        """Populating `body_html`"""
        body_html = self.get_email().replace("{{css}}", self.get_css())
        try:
            for key, value in replace_dict.items():
                body_html = body_html.replace(f"{{{{{key}}}}}", str(value))
            self.mk1.logging.logger.info("(GoogleEmailAPI.populate_body_message) The body message was populated successfully")
            return body_html
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.populate_body_message) Message creation failed: {e}")
            raise

    def build_message(self, email_from: str, email_to: str, email_subject: str) -> Dict[str, str]:
        """Builds and encodes the email message"""
        body_html = self.populate_body_message({})
        try:
            msg = MIMEText(body_html, "html")
            msg["subject"] = email_subject
            msg["from"] = email_from
            msg["to"] = email_to
            encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            self.mk1.logging.logger.info("(GoogleEmailAPI.build_message) Message built successfully")
            return {'raw': encoded_msg}
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.build_message) Message creation failed: {e}")
            raise

    def send_message(self, email_from: str, email_to: str, email_subject: str) -> Optional[Dict]:
        """Sends an email message"""
        try:
            msg = self.build_message(email_from, email_to, email_subject)
            send = self.service.users().messages().send(
                userId='me',  # Adjust as needed for different userId
                body=msg
            ).execute()
            self.mk1.logging.logger.info("(GoogleEmailAPI.send_message) Message sent successfully")
            return send
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.send_message) Message sending failed: {e}")
            raise

    def get_emails_from_past_days(self, user_id: str, num_hours: int) -> List[Dict]:
        """Fetches emails from the past `num_hours`"""
        try:
            end_date           = datetime.now()
            start_date         = end_date - timedelta(hours=num_hours)
            start_datetime_utc = start_date.replace(tzinfo=timezone.utc)
            end_datetime_utc   = end_date.replace(tzinfo=timezone.utc)
            start_time_seconds = int(start_datetime_utc.timestamp())
            end_time_seconds   = int(end_datetime_utc.timestamp())

            query = f"after:{start_time_seconds} before:{end_time_seconds} in:inbox category:primary"
            response = self.service.users().messages().list(
                userId = user_id,
                q = query
            ).execute()
            messages = response.get('messages', [])
            self.mk1.logging.logger.info(f"(GoogleEmailAPI.get_emails_from_past_days) Retrieved {len(messages)} messages from the past {num_hours} hours")
            return messages
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.get_emails_from_past_days) Failed to retrieve emails: {e}")
            return []

    def get_emails_with_keywords(self, user_id: str, query: str) -> List[Dict]:
        """Fetches emails that match the given query"""
        try:
            response = self.service.users().messages().list(
                userId=user_id,
                q=query
            ).execute()
            messages = response.get('messages', [])
            self.mk1.logging.logger.info(f"(GoogleEmailAPI.get_emails_with_keywords) Retrieved {len(messages)} messages with query: {query}")
            return messages
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.get_emails_with_keywords) Failed to retrieve emails: {e}")
            return []


    def extract_raw_data_from_html(self, html_content : str):
        soup = BeautifulSoup(html_content, 'html.parser')
        # Extract plain text from HTML
        text_content = soup.get_text(separator='\n').strip()
        return text_content

    def decode_message(self, text: str):
        """Helper function to decode Base64 content"""
        try:
            return base64.urlsafe_b64decode(text).decode('utf-8')
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.decode_message) Failed to decode message: {e}")
            return None


    def get_email_body(self, content: Dict) -> Optional[str]:
        """Extracts the body of the email from the content"""
    
        try:
            html_part = None
            plain_text_part = None
            
            # Check if the email contains parts (multiple sections such as plain text and HTML)
            if 'parts' in content.get('payload', {}):
                for part in content['payload']['parts']:
                    mime_type = part.get('mimeType', '')
                    if mime_type == 'text/html':  # Prioritize HTML
                        html_part = part['body'].get('data', '')
                    elif mime_type == 'text/plain':  # Store plain text as fallback
                        plain_text_part = part['body'].get('data', '')

                # Decode HTML part if it exists
                if html_part:
                    text = self.decode_message(html_part)
                    text = self.extract_raw_data_from_html(text)
                    return text

                # If no HTML part, fallback to plain text
                if plain_text_part:
                    text = self.decode_message(plain_text_part)
                    return text
            
            # Fallback to single-part body (could be plain text or HTML directly)
            if "data" in content.get('payload', {}).get('body', {}):
                message = content['payload']['body']['data']
                text = self.decode_message(message)
                return text

            self.mk1.logging.logger.info("(GoogleEmailAPI.get_email_body) Email body has no data.")
            return None

        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.get_email_body) Failed to get email body: {e}")
            return None



    def get_email_sender(self, response: Dict) -> Optional[str]:
        """Extracts the sender of the email"""
        try:
            headers = response.get('payload', {}).get('headers', [])
            for header in headers:
                if header.get('name') == 'From':
                    value = header.get('value', '')
                    if '<' in value:
                        return value.split("<")[1].split(">")[0]
                    return value
            return None
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.get_email_sender) Failed to get email sender: {e}")
            return None

    def get_email_text_info(self, user_id: str, email_id: str) -> Dict[str, Union[str, int]]:
        """Fetches detailed information about a specific email"""
        try:
            response = self.service.users().messages().get(
                userId = user_id,
                id     = email_id
            ).execute()

            email_info = {
                'date'      : response.get('internalDate', ''),
                'label_ids' : response.get('labelIds', []),
                'subject'   : response.get('snippet', ''),
                'from'      : self.get_email_sender(response),
                'body'      : self.get_email_body(response),
            }
            self.mk1.logging.logger.info(f"(GoogleEmailAPI.get_email_text_info) Retrieved email info for ID: {email_id}")
            return email_info
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.get_email_text_info) Failed to retrieve email info: {e}")
            return {}

    def delete_email_by_id(
            self, 
            user_id: str, 
            email_id: str) -> None:
        """
            Deletes an email from the Gmail account using the email ID.

            Args:
                user_id (str): The ID of the Gmail user (typically 'me' to indicate the authenticated user).
                email_id (str): The unique ID of the email to delete.

            Returns:
                None
        """
        try:
            # Deleting the email with the given ID
            self.service.users().messages().delete(
                userId = user_id, 
                id     = email_id
            ).execute()
            self.mk1.logging.logger.info(f"(GoogleEmailAPI.delete_email_by_id) Deleted email with ID: {email_id}")
        except Exception as e:
            # Log any errors that occur during the deletion process
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.delete_email_by_id) Failed to delete email with ID: {email_id} - {e}")

    def archive_email_by_id(
            self, 
            user_id: str, 
            email_id: str) -> None:
        """
        Archives an email from the Gmail account using the email ID.

        Args:
            user_id (str): The ID of the Gmail user (typically 'me' to indicate the authenticated user).
            email_id (str): The unique ID of the email to archive.

        Returns:
            None
        """
        try:
            # Archiving the email by modifying its labels
            self.service.users().messages().modify(
                userId=user_id,
                id=email_id,
                body={
                    'removeLabelIds': ['INBOX']  # Remove from INBOX to archive
                }
            ).execute()
            self.mk1.logging.logger.info(f"(GoogleEmailAPI.archive_email_by_id) Archived email with ID: {email_id}")
        except Exception as e:
            raise e
            # Log any errors that occur during the archiving process
            self.mk1.logging.logger.error(f"(GoogleEmailAPI.archive_email_by_id) Failed to archive email with ID: {email_id} - {e}")


# -------------------------------------- 3. (GOOGLE) DOCS ----------------------------------------- #
class GoogleDocsAPI(GoogleAPI):
    """
    API for using Google Docs efficiently through Python.

    [GET]
        1. `get_document` -

    [POST]
        1. `append_text_to_document` -
    """
    
    def __init__(self, mk1, google_api):
        self.mk1 = mk1

        ## __________ *** Initializing (attributes) *** __________
        self.service_name = mk1.config.get("api_google_docs","service_name")
        self.version      = mk1.config.get("api_google_docs","version")
        self.credentials  = google_api.credentials
        self.auth_header  = google_api.auth_header

        ## __________ *** Initializing (client) *** __________
        self.service = self.build_client()

    def build_client(self):
        """Builds the Google Docs API client."""
        try:
            service = build(
                serviceName=self.service_name,
                version=self.version,
                credentials=self.credentials,
                cache_discovery=False
            )
            self.mk1.logging.logger.info("(GoogleDocsAPI.build_client) Service build succeeded")
            return service
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDocsAPI.build_client) Service build failed: {e}")
            return None

    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Fetches a document by its ID."""
        try:
            response = self.service.documents().get(documentId=document_id).execute()
            document_info = {'content': response.get('body', {}).get('content', [])}
            self.mk1.logging.logger.info(f"(GoogleDocsAPI.get_document) Retrieved document `{document_id}` successfully")
            return document_info
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDocsAPI.get_document) Failed to retrieve document `{document_id}`: {e}")
            return {}





    def wrap_text_as_new_paragraph(self, text_content: str) -> Dict[str, Any]:
        """Wraps text content as a new paragraph for Google Docs API."""
        return {
            'paragraph': {
                'elements': [
                    {
                        'textRun': {
                            'content': text_content,
                        }
                    }
                ]
            }
        }

    def append_text_to_document(
            self, 
            document_id: str, 
            text_content: str, 
            start_index: int, 
            heading_id: str = "NORMAL_TEXT",
            font_family: str = "Proxima Nova",  # Optional font family
            font_size: int = None,  # Optional font size in points
            bold: bool = False,  # Optional bold
            italic: bool = False,  # Optional italic
            underline: bool = False,  # Optional underline
            num_enters: int = 1
        ) -> Dict[str, Any]:
        """Appends text with specific style to a document at a specific index."""
        
        # Mapping from heading_id to Google Docs named styles
        heading_styles = {
            'HEADING_1'   : 'HEADING_1',
            'HEADING_2'   : 'HEADING_2',
            'HEADING_3'   : 'HEADING_3',
            'HEADING_4'   : 'HEADING_4',
            'HEADING_5'   : 'HEADING_5',
            'HEADING_6'   : 'HEADING_6',
            'NORMAL_TEXT' : 'NORMAL_TEXT',  # Default style
            'TITLE'       : 'HEADING_1',          # Use HEADING_1 for Title
            'SUBTITLE'    : 'HEADING_2'        # Use HEADING_2 for Subtitle
        }
        
        if heading_id not in heading_styles:
            self.mk1.logging.logger.error(f"(GoogleDocsAPI.append_text_to_document) Invalid heading_id: {heading_id}")
            return {}

        try:
            # Define the requests to insert text
            requests = [
                {
                    'insertText': {
                        'location': {'index': start_index},
                        'text': "\n" * num_enters + text_content,
                    }
                }
            ]

            # Apply the specified paragraph style
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': start_index + len(text_content) + num_enters
                    },
                    'paragraphStyle': {
                        'namedStyleType': heading_styles[heading_id]  # Apply the specified paragraph style
                    },
                    'fields': 'namedStyleType'
                }
            })

            # Apply text formatting if specified
            text_style = {
                'weightedFontFamily': {
                    'fontFamily': font_family
                } if font_family else None,
                'fontSize': {
                    'magnitude': font_size,
                    'unit': 'PT'
                } if font_size else None,
                'bold': bold,
                'italic': italic,
                'underline': underline
            }
            text_style = {k: v for k, v in text_style.items() if v is not None}  # Clean up None values

            if text_style:
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': start_index,
                            'endIndex': start_index + len(text_content) + num_enters
                        },
                        'textStyle': text_style,
                        'fields': ','.join(text_style.keys())
                    }
                })

            # Send batchUpdate request to the Google Docs API
            response = self.service.documents().batchUpdate(
                documentId=document_id,
                body={'requests': requests}
            ).execute()

            style_info = f" with style `{heading_id}`" if heading_id else " with default style"
            font_info = f", font family `{font_family}`" if font_family else ""
            font_size_info = f", font size `{font_size}`pt" if font_size else ""
            formatting_info = f"{font_info}{font_size_info}"
            self.mk1.logging.logger.info(f"(GoogleDocsAPI.append_text_to_document) Appended text to document `{document_id}`{style_info}{formatting_info} successfully")
            return response

        except Exception as e:
            raise e
            self.mk1.logging.logger.error(f"(GoogleDocsAPI.append_text_to_document) Failed to append text to document `{document_id}`: {e}")
            return {}
                
# -------------------------------------- 4. (GOOGLE) DRIVE ----------------------------------------- #
class GoogleDriveAPI(GoogleAPI):
    """
    API for using Google Drive efficiently through Python.
    
    [Utilities]
        1. `build_client` - Initializes the Google Drive API client.
        2. `mime_to_str` - Converts MIME type to a human-readable string.
        3. `str_to_mime` - Converts human-readable string to MIME type.
        4. `datetime_to_ISO8601` - Converts datetime object to ISO8601 string format.
        5. `build_query` - Constructs a query string for Google Drive API requests.

    [GET]
        1. `get_file` - Retrieves file metadata.

    [POST]
        1. `copy_file` - Creates a copy of a file.
        2. `upload_file` - Uploads a file to a specified folder.
        3. `enable_sharable_link` - Enables a sharable link for a file.
    
    [UPDATE]
        1. `update_file` - Updates file metadata.
        2. `change_file_name` - Changes the name of a file.
        
    [DELETE]
        1. `delete_all_files_in_folder` - Deletes all files in a specified folder.
    """

    def __init__(self, mk1, google_api):
        self.mk1 = mk1
        
        ## __________ *** Initializing (attributes) *** __________
        self.service_name = self.mk1.config.get("api_google_drive", "service_name")
        self.version      = self.mk1.config.get("api_google_drive", "version")
        self.credentials  = google_api.credentials
        self.auth_header  = google_api.auth_header
        
        ## __________ *** Initializing (client) *** __________
        self.service = self.build_client()

    def build_client(self):
        """Initialize the Google Drive API client."""
        try:
            service = build(
                serviceName=self.service_name,
                version=self.version,
                credentials=self.credentials,
                cache_discovery=False
            )
            self.mk1.logging.logger.info("(GoogleDriveAPI.build_client) Service build succeeded")
        except Exception as e:
            service = None
            self.mk1.logging.logger.error(f"(GoogleDriveAPI.build_client) Service build failed: {e}")
        return service

    def mime_to_str(self, mime_type: str) -> str:
        """Convert MIME type to a human-readable string."""
        mime_types = {
            "application/vnd.google-apps.document": "google_doc",
            "application/vnd.google-apps.drawing": "google_drawing",
            "application/vnd.google-apps.spreadsheet": "google_sheets",
            "application/vnd.google-apps.presentation": "google_slides",
            "application/vnd.google-apps.form": "google_form",
            "application/vnd.google-apps.file": "drive_file",
            "application/vnd.google-apps.folder": "drive_folder",
            "application/vnd.google-apps.script": "apps_script"
        }
        return mime_types.get(mime_type, "unknown")

    def str_to_mime(self, mime_str: str) -> str:
        """Convert human-readable string to MIME type."""
        mime_strings = {
            "google_doc": "application/vnd.google-apps.document",
            "google_drawing": "application/vnd.google-apps.drawing",
            "google_sheets": "application/vnd.google-apps.spreadsheet",
            "google_slides": "application/vnd.google-apps.presentation",
            "google_form": "application/vnd.google-apps.form",
            "drive_file": "application/vnd.google-apps.file",
            "drive_folder": "application/vnd.google-apps.folder",
            "apps_script": "application/vnd.google-apps.script"
        }
        return mime_strings.get(mime_str, "unknown")

    def datetime_to_ISO8601(self, datetime_obj):
        """Convert datetime object to ISO8601 string format."""
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S%z")

    def build_query(self, folder_id: str, name: str = None, trashed: bool = False, mime: str = None) -> str:
        """Construct a query string for Google Drive API requests."""
        query = f"'{folder_id}' in parents and trashed={str(trashed).lower()}"
        if name:
            query += f" and name contains '{name}'"
        if mime:
            query += f" and mimeType='{self.str_to_mime(mime)}'"
        self.mk1.logging.logger.info("(GoogleDriveAPI.build_query) Query constructed successfully")
        return query

    def get_file(self, file_id: str, fields: str = "id,name,mimeType") -> Dict:
        """Retrieve file metadata."""
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields={fields}"
        try:
            response = requests.get(url, headers=self.auth_header)
            result = self.request_check(response)
            file_info = json.loads(result.text)
            self.mk1.logging.logger.info(f"(GoogleDriveAPI.get_file) Retrieved file metadata successfully for file_id: {file_id}")
            return {
                "file_id": file_info["id"],
                "file_name": file_info["name"],
                "file_type": self.mime_to_str(file_info["mimeType"])
            }
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDriveAPI.get_file) Getting file failed: {e}")
            raise e

    def upload_file(self, folder_id: str, fn_path: str, kind: str = "png") -> str:
        """Upload a file to a specified folder."""
        try:
            file_metadata = {
                "name": fn_path.split("/")[-1],
                "parents": [folder_id]
            }
            media = MediaFileUpload(fn_path, mimetype=f"image/{kind}")
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            self.mk1.logging.logger.info(f"(GoogleDriveAPI.upload_file) File {fn_path} uploaded successfully")
            return file.get("id")
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDriveAPI.upload_file) File {fn_path} uploading failed: {e}")
            raise e

    def enable_sharable_link(self, file_id: str) -> str:
        """Enable a sharable link for a file."""
        try:
            request_body = {
                'role': 'reader',
                'type': 'anyone'
            }
            self.service.permissions().create(fileId=file_id, body=request_body).execute()
            response_link = self.service.files().get(fileId=file_id, fields='webViewLink').execute()
            self.mk1.logging.logger.info(f"(GoogleDriveAPI.enable_sharable_link) Sharable link enabled successfully for file_id: {file_id}")
            return response_link["webViewLink"]
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDriveAPI.enable_sharable_link) File's {file_id} URL retrieval failed: {e}")
            raise e

    def copy_file(self, file_id: str, parent_folder: str) -> Dict:
        """Create a copy of a file."""
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/copy"
        body = {
            "parents": [parent_folder],
            "mimeType": "application/vnd.google-apps.spreadsheet"
        }
        try:
            response = requests.post(url, headers=self.auth_header, data=json.dumps(body))
            result = self.request_check(response)
            file_info = json.loads(result.text)
            self.mk1.logging.logger.info(f"(GoogleDriveAPI.copy_file) File copied successfully from file_id: {file_id} to parent_folder: {parent_folder}")
            return {
                "copy_id": file_info["id"],
                "copy_name": file_info["name"],
                "copy_type": self.mime_to_str(file_info["mimeType"])
            }
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDriveAPI.copy_file) Copying file failed: {e}")
            raise e

    def update_file(self, file_id: str, new_name: str = None, add_parent: str = None, remove_parent: str = None) -> Dict:
        """Update file metadata."""
        body = {"name": new_name}
        try:
            result = self.service.files().update(
                fileId=file_id,
                addParents=add_parent,
                removeParents=remove_parent,
                body=body
            ).execute()
            self.mk1.logging.logger.info(f"(GoogleDriveAPI.update_file) File updated successfully with file_id: {file_id}")
            return {
                "update_id": result.get("id"),
                "update_name": result.get("name"),
                "update_type": self.mime_to_str(result.get("mimeType"))
            }
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDriveAPI.update_file) Updating file failed: {e}")
            raise e

    def delete_all_files_in_folder(self, folder_id: str):
        """Delete all files in a specified folder."""
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        try:
            # Retrieve the list of files to be deleted
            res = self.service.files().list(
                q=query,
                fields="files(id)",
                corpora="allDrives",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageSize=1000
            ).execute()
            
            files = res.get("files", [])
            if not files:
                self.mk1.logging.logger.info(f"(GoogleDriveAPI.delete_all_files_in_folder) No files found in folder {folder_id}.")
            
            for file in files:
                try:
                    # Delete each file
                    self.service.files().delete(fileId=file["id"]).execute()
                    self.mk1.logging.logger.info(f"(GoogleDriveAPI.delete_all_files_in_folder) File {file['id']} deleted successfully.")
                except Exception as e:
                    self.mk1.logging.logger.error(f"(GoogleDriveAPI.delete_all_files_in_folder) Failed to delete file {file['id']}: {e}")

            self.mk1.logging.logger.info(f"(GoogleDriveAPI.delete_all_files_in_folder) All files in folder {folder_id} deleted successfully.")

        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDriveAPI.delete_all_files_in_folder) Failed to retrieve or delete files in folder {folder_id}: {e}")
            raise e


    def change_file_name(self, file_id: str, new_name: str) -> Dict:
        """
        Change the name of a file in Google Drive.

        :param file_id: ID of the file to update.
        :param new_name: New name to set for the file.
        :return: A dictionary with the updated file ID and name.
        """
        body = {
            "name": new_name
        }
        
        try:
            result = self.service.files().update(
                fileId=file_id,
                body=body
            ).execute()
            self.mk1.logging.logger.info(f"(GoogleDriveAPI.change_file_name) File name changed successfully")
            return {
                "file_id": result.get("id"),
                "file_name": result.get("name"),
                "file_type": self.mime_to_str(result.get("mimeType"))
            }
        except Exception as e:
            self.mk1.logging.logger.error(f"(GoogleDriveAPI.change_file_name) File name change failed: {e}")
            raise e