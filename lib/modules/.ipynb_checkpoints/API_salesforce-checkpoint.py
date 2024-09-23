#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""
    [*] Description     : A simple wrapper module for Salesforce API
    [*] Original Author : anton@uber.com, jason.schwebel@uber.com
    [*] Author          : dimitrios.georgiou@uber.com 
    [*] Date (created)  : 
    [*] Date (modified) : Feb 7, 2023
    [*] Links       :  
        1. https://code.uberinternal.com/diffusion/ANKRAQO/browse/master/USC_EATS/asavitski/exclusivity_deals_alerts/salesforce.py
        2. https://code.uberinternal.com/diffusion/ANKRAQO/browse/master/USC_EATS/asavitski/exclusivity_deals_alerts/salesforce.py
        3. https://michelangelo-studio.uberinternal.com/file/13f05f84-72e3-4457-9eac-2792079c1c48
"""
# -*-*-*-*-*-*-*-*-*-*-* #
#     Basic Modules      #
# -*-*-*-*-*-*-*-*-*-*-* #
import os, re, json, yaml, time, requests, urllib
import pandas as pd

from typing   import List, Tuple, Any, Dict
from io       import StringIO

# -*-*-*-*-*-*-*-*-*-*-*-* #
#     Modules for API      #
# -*-*-*-*-*-*-*-*-*-*-*-* #



class Requests(object):
    def __init__(self):
        pass

    # Status Methods
    def status_check(self, response, has_payload = True, is_json = True):
        if 100 <= response.status_code <= 199: # Info
            raise Exception("Informational Error")
            
        elif 200 <= response.status_code <= 299: # Success
            if has_payload:
                if is_json:
                    return json.loads(response.text)
                else:
                    return response.text
            else:
                return None
        elif 300 <= response.status_code <= 399: # Redirect
            raise Exception("Redirection Error")
            
        elif 400 <= response.status_code <= 499: # Client Error
            raise Exception(f"Client Side Error - {response.status_code}")
            
        elif 500 <= response.status_code <= 599: # Server Error
            raise Exception(f"Server Side Error - {response.status_code}")
            
        else:
            raise Exception("Unknown Error")
            
        
    

class SalesforceAPI(Requests):
    def __init__(self, mk1):
        # System Design 
        self.mk1 = mk1
        
        ## *-*-*-*- Initializing Attributes *-*-*-*- ##
        # Secrets 
        self.prod_instance     = str(mk1.config.get("api_salesforce","prod_instance"))      # Instance
        self.prod_view_url     = str(mk1.config.get("api_salesforce","prod_view_url"))
        self.prod_secrets_path = str(mk1.config.get("api_salesforce","prod_secrets_path")) 
        
        ## *-*-*-*- Secrets/Credentials Info *-*-*-*- ##
        secrets_payload        = self.get_credentials()
        self.client_id         = secrets_payload["prod_client_id"]
        self.client_secret     = secrets_payload["prod_client_secret"]
        self.refresh_token     = secrets_payload["prod_refresh_token"]
        
        # self.client_id     = str(mk1.config.get("api_salesforce","prod_client_id")) 
        # self.client_secret = str(mk1.config.get("api_salesforce","prod_client_secret")) 
        # self.refresh_token = str(mk1.config.get("api_salesforce","prod_refresh_token"))
        
        ## *-*-*-*- Session Info *-*-*-*- ##        
        #self.session_id, self.instance_url, self.access_token, self.headers = self.authenticate()
        authentication_payload = self.authenticate()
        self.session_id        = authentication_payload["id"]
        self.instance_url      = authentication_payload["instance_url"]
        self.access_token      = authentication_payload["access_token"]
        self.token_type        = authentication_payload["token_type"]
        self.headers           = self.get_headers()
        
        # counters
        self.calls_counter = 0 #v8.1
        self.puts_counter  = 0 #v8.1
        


    ## *-*-*-*-*-*-*-*-* ##
    ##      SESSION      ##
    ## *-*-*-*-*-*-*-*-* ##
    def get_credentials(self):
    
        prod_secrets_path = os.environ['SECRETS_PATH'] + self.prod_secrets_path
        
        with open(prod_secrets_path, 'r') as f:
            payload = yaml.load(f.read(), yaml.FullLoader) 
            return payload
    
    
    def get_headers(self):
        headers = {
            'Content-type'  : "application/json; charset=UTF-8",
            'Authorization' : f"{self.token_type} {self.access_token}", # 'Bearer',
            'X-PrettyPrint' : '1'
        }
        return headers
    
    
    def authenticate(self):
        ## *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url  = f"https://{self.prod_instance}.salesforce.com/services/oauth2/token" # "https://login.salesforce.com/services/oauth2/token"
        body = {
            "grant_type"    : "refresh_token", 
            "client_id"     : self.client_id, 
            "client_secret" : self.client_secret, 
            "refresh_token" : self.refresh_token
        }
        
        print(url, body)
        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##
        try:
            response = requests.post(url, data = body)
            payload  = self.status_check(response)
            
            if "error" in payload:
                error             = payload["error"]
                error_description = payload["error_description"]
                self.mk1.logging.logger.error(f"(SalesforceAPI.authenticate) Connecting to Salesforce API failed : {error} | {error_description}")
                return None
            
            else : 
                self.mk1.logging.logger.info(f"(SalesforceAPI.authenticate) Successfully connected to Salesforce API !")
                return payload
        
        except Exception as e : 
            self.mk1.logging.logger.error(f"(SalesforceAPI.authenticate) Connecting to Salesforce API failed : {e}")
            return None
            #raise e
            
    ## *-*-*-*-*-*-*-*-* ##
    ##    UTILITIES      ##
    ## *-*-*-*-*-*-*-*-* ##
    def df_to_csv(
            self, 
            df  : pd.DataFrame, 
        ):
        # Use StringIO to write the contents of the DataFrame to a CSV-formatted string
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index = False)
        # Get the contents of the StringIO object
        return csv_buffer.getvalue()
    
    
    def csv_to_df(self, csvstring, sep = ','):
        df = pd.read_csv( StringIO(csvstring), sep =',')
        return df
    
    
    def build_simple_soql(self, 
            _select : List[str] = [], 
            _from   : str       = "", 
            _where  : str       = "", 
            _in     : List[str] = []
        ) -> str:
        """ Building simple SOQL
            Args
            ----
                :param: `_select` - A list with all the fields/attributes we want from the table
                :param: `_from`   - The respective table we are querying
                :param: `_where   - All the underlying filtering/exceptions for the query "WHERE"
                :param: `_in`     - All the underlying filtering/exceptions for the query "IN"
                
            Returns
            -------
                :returns: `soql_str`  - The underlying query SQL string
        """       
        _select  = ",".join(_select)
        _in      =  "'"+"','".join(in_field)+"'"
        soql_str = f"""SELECT {_select} FROM {_from} WHERE {_where} in ({_in})"""
        return soql_str
    
    def set_soql(self, 
            soql_path : str
        ) -> str:
        """ Reads an sql string from file"""
        with open(soql_path, "r") as _file: # No need to close file
            soql_path = _file.read()
        return soql_path

    def id_validation(
            self, 
            email_list : List[str]
        ) -> List[str]:
        """Validates email and/or salesforce owner id"""
        reg    = re.compile(r'^[a-zA-Z0-9]{15,18}$|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        emails = [re.match(reg, i).group() for i in email_list if re.match(reg, i) is not None]
        return emails
    
    def divide_chunks(
            self, 
            id_list : List[str] = [], 
            _n      : int = 800
        ): 
        """ Divides list in chunks of n element for SOQL queries"""
        # looping till length l
        for i in range(0, len(id_list), _n):
            yield id_list[i:i + _n]
            
            
   
          
    
    ## *-*-*-*-*-*-*-*-* ##
    ##   GET Requests    ##
    ## *-*-*-*-*-*-*-*-* ##
    def get_request_urls(self) : 
        urls = {
            "production"       : "https://uber.lightning.force.com/lightning/r/{sobject}/{sobject_id}/view",
            "query"            : self.instance_url + "/services/data/v49.0/query?q={soql_str}",
            "query_by_sobject" : self.instance_url + "/services/data/v49.0/composite/sobjects/{sobject}?ids={sobject_ids_chunk}&fields={sobject_fields}",
            "sobject_data"     : self.instance_url + "/services/data/v52.0/sobjects/{sobject}/{sobject_id}",
            "report"           : self.instance_url + "/services/data/v55.0/analytics/reports/{report_id}",
            "limits"           : self.instance_url + "/services/data/v49.0/limits/"
            
        }
        return urls
    
    def get_limits(self):
        """Get the limits for existing session in Salesforce
        
            Returns
            -------
                :returns: `payload` - The response dictionary

        """ 
        ## *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + "/services/data/v49.0/limits/"
      
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##
        try : 
            response = requests.get(
                url     = url, 
                headers = self.headers, 
                cookies = {"sid": self.session_id}
            )
            payload  = self.status_check(response, is_json = False)
            #print(f"(SalesforceAPI.get_limits) Getting limits is successful !")
            self.mk1.logging.logger.info(f"(SalesforceAPI.get_limits) Getting limits is successful !")
            return payload
        
        except Exception as e : 
            #print(f"(SalesforceAPI.get_report) Getting limits failed: {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.get_report) Getting limits failed: {e}")
            raise e

        
        
    def query(
            self, 
            soql_str : str
        ) -> pd.DataFrame:
        """ Querying with SQL query 
        
            Args
            ----
                :param: `soql_str` - The SOQL in a string format
                
            Returns
            -------
                :returns: `payload` - The response dataframe with all the requested fields (columns) for all sobjects (sobject_ids)
        
        """
        
        ## *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + "/services/data/v49.0/query?q=" + urllib.parse.quote_plus(soql_str)

        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##
        try:
            response = requests.get(
                url     = url, 
                headers = self.headers
            )
            payload  = self.status_check(response)
            
            if not payload["done"]:
                next_url = payload.get("nextRecordsUrl") # Getting next query URL
             
                # Looping query records and appending to payload
                while True:
                    ## *-*-*-*-*-*-*-*-*- [record] Requesting -*-*-*-*-*-*-*-*-* ##
                    response_record = requests.get(
                        url     = self.instance_url + next_url, 
                        headers = self.headers
                    )
                    payload_record  = self.status_check(response_record)
                    
                    ## *-*-*-*-*-*-*-*-*- [record] Formatting the result -*-*-*-*-*-*-*-*-* ##       
                    payload["records"] += payload_record["records"] 
                    if payload_record["done"] : break
                    next_url = payload_record.get("nextRecordsUrl")
                    self.calls_counter += 1  # count number of sf calls
            
            ## *-*-*-*-*-*-*-*-*- [record] Formatting the result -*-*-*-*-*-*-*-*-* ##       
            [p.pop('attributes') for p in payload['records']] #  converting payload to DataFrame
            
            #print(f"(SalesforceAPI.query) The SQL query {soql_str} returned # {payload.shape[0]} rows !")
            self.mk1.logging.logger.info(f"(SalesforceAPI.query) The SQL query {soql_str} returned # {len(payload)} rows !")
            return pd.DataFrame(payload['records'])
            #return payload['records'][0] #pd.DataFrame(payload['records'])
                
        except Exception as e:
            #print(f"(SalesforceAPI.query) The execution of the SQL query {soql_str} failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.query) The execution of the SQL query {soql_str} failed : {e}") 
            raise e
            
            
            
    def query_by_sobject(
            self, 
            sobject        : str       = 'Account',
            sobject_ids    : List[str] = [""], 
            sobject_fields : List[str] = ['UUID__c','Id', 'ParentId'], 
        ) -> pd.DataFrame:
        
        """ Query by SOBJECT
        
            Args
            ----
                :param: `sobject`        - The type of the existing SOBJECT. Options ~ {Contact, Account, User, Opportunity}
                :param: `sobject_id`     - The respective id of the existing SOBJECT
                :param: `sobject_fields` - The features of the existing SOBJECT we want to retrieve information
                
            Returns
            -------
                :returns: `payload` - The response dataframe with all the requested fields (columns) for all users (sobject_ids)
        
        
        
        """
       
        sobject_ids_chunked = list(self.divide_chunks(sobject_ids)) # max chunk size 800 ids
        payload             = []

        try:
            for sobject_ids_chunk in sobject_ids_chunked:
                ## *-*-*-*-*-*-*-*-*- [chunk] Configuration (attributes) -*-*-*-*-*-*-*-*-* ##
                sobject_ids_chunk = ",".join(sobject_ids_chunk)
                sobject_fields    = ','.join(sobject_fields)
                
              
                ## *-*-*-*-*-*-*-*-*- [chunk] Creating the request -*-*-*-*-*-*-*-*-* ##
                url = self.instance_url + f"/services/data/v49.0/composite/sobjects/{sobject}?ids={sobject_ids_chunk}&fields={sobject_fields}"

                ## *-*-*-*-*-*-*-*-*- [chunk] Requesting -*-*-*-*-*-*-*-*-* ##       
                response = requests.get(
                    url     = url, 
                    headers = self.headers
                )
                
                ## *-*-*-*-*-*-*-*-*- [chunk] Formatting the result -*-*-*-*-*-*-*-*-* ##       
                payload_chunk       = self.status_check(response) # Response is a dictionary
                payload            += payload_chunk
                self.calls_counter += 1 # count number of sf calls

            ## *-*-*-*-*-*-*-*-*- Formatting the result -*-*-*-*-*-*-*-*-* ##       
            for payload_chunk in payload : payload_chunk.pop('attributes', None)
            
            #print(f"(SalesforceAPI.queryBySobject) Querying the features [{sobject_fields}] from {len(sobject_ids)} {sobject}(s)  was successful!")
            self.mk1.logging.logger.info(f"(SalesforceAPI.queryBySobject) Querying the features [{sobject_fields}] from {len(sobject_ids)} {sobject}(s)  was successful!")
            return payload[0] #pd.DataFrame(payload)
        
        
        except Exception as e:
            #print(f"(SalesforceAPI.queryBySobject) Querying the features [{sobject_fields}] from {len(sobject_ids)} {sobject}(s) failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.queryBySobject) Querying the features [{sobject_fields}] from `{len(sobject_ids)} {sobject}(s) failed : {e}")
            raise e
            
            
    def get_sobject_data(self, 
            sobject    : str, 
            sobject_id : str
        ):
        """ Getting data of an existing SOBJECT. Sobject can be Contact, Account, User, Opportunity, etc
        
            Args
            ----
                :param: `sobject`    - Options ~ {Contact, Account, User, Opportunity, Case}
                :param: `sobject_id` - The respective id of the existing SOBJECT
        
            
            Returns
            -------
                :returns: `payload` - The response dictionary
        
        """
        
        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + f"/services/data/v52.0/sobjects/{sobject}/{sobject_id}"
        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##
        try : 
            response = requests.get(
                url, 
                headers = self.headers, 
                cookies = {"sid": self.session_id}
            )
            payload  = self.status_check(response)
            payload.pop('attributes', None)

            #print(f"(SalesforceAPI.get_sobject_data) Getting the sobject data for {sobject}'s `{sobject_id}` was successful!")
            self.mk1.logging.logger.info(f"(SalesforceAPI.get_sobject_data) Getting the sobject data for {sobject}'s `{sobject_id}` was successful!")
            return payload # pd.DataFrame(payload, index = [0]).T
        
        except Exception as e : 
            #print(f"(SalesforceAPI.get_sobject_data) Getting the sobject data  for {sobject}'s `{sobject_id} failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.get_sobject_data) Getting the sobject data  for {sobject}'s `{sobject_id} failed : {e}")
            raise e
            
            
            
            
            
    def get_queue_cases(
            self,
            queue_id : str
        ) :
        """
        """
         
        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + f"/services/data/v52.0/sobjects/Case/list?filterName={queue_id}"
        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##
        try : 
            response = requests.get(
                url, 
                headers = self.headers, 
                cookies = {"sid": self.session_id}
            )
            payload  = self.status_check(response)

            #print(f"(SalesforceAPI.get_queue_cases) Getting all the cases for the queue/collection `{queue_id}` was successful!")
            self.mk1.logging.logger.info(f"(SalesforceAPI.get_queue_cases) Getting all the cases for the queue/collection `{queue_id}` was successful!")
            return payload 
        
        except Exception as e : 
            #print(f"(SalesforceAPI.get_queue_cases)  Getting all the cases for the queue/collection `{queue_id}`  failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.get_queue_cases) Getting all the cases for the queue/collection `{queue_id}` failed : {e}")
            raise e
 
    


   
    ## *-*-*-*-*-*-*-*-* ##
    ##   PATCH Requests  ##
    ## *-*-*-*-*-*-*-*-* ##
    
    def update_sobject(self, 
            sobject        : str           = "",
            sobject_id     : str           = "",
            sobject_fields : Dict[str,Any] = {}
        ) : 
        """ Updates an existing SOBJECT
            Args
            ----
                :param: `sobject`        - The type of the existing SOBJECT. Options ~ {Contact, Account, User, Opportunity, Case}
                :param: `sobject_id`     - The respective id of the existing SOBJECT
                :param: `sobject_fields` - The salesforce dictionary with info for the existing SOBJECT (eg. name, type)
        
            
            Returns
            -------
                :returns: `payload` - The response dictionary
        """
                                                                                                            
        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + f"/services/data/v49.0/sobjects/{sobject}/{sobject_id}"
        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##
        try:
  
            response = requests.patch(
                url     = url, 
                headers = self.headers, 
                data    = json.dumps(sobject_fields)
            )    
            payload = self.status_check(response, has_payload = False)
            self.puts_counter += 1
            #print(f"(SalesforceAPI.update_sobject) Updating the sobject {sobject}'s `{sobject_id}`  was successful !")
            self.mk1.logging.logger.info(f"(SalesforceAPI.update_sobject) Updating the sobject {sobject}'s `{sobject_id}`  was successful !")
            return payload

        
        except Exception as e : 
            #print(f"(SalesforceAPI.update_sobject) Updating the sobject {sobject}'s `{sobject_id}`  failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.update_sobject) Updating the sobject {sobject}'s `{sobject_id}`  failed : {e}")
            raise e
                    
                
 
    ## *-*-*-*-*-*-*-*-* ##
    ##   POST Requests   ##
    ## *-*-*-*-*-*-*-*-* ##
    
    def get_report(
            self, 
            report_id     : str           = "",
            report_fields : Dict[str,Any] = {}
        ):
        """ Get a report based on a specific `report_id` and specific filters
        
            Args
            ----
                :param: `report_id`     - The str ID of the report
                :param: `report_fields` - The the fiels of the report we are requesting
                
            Returns
            -------
                :returns: `payload` - The response dictionary

        """    
        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + f"/services/data/v55.0/analytics/reports/{report_id}"
        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##
        try : 
            response = requests.get(
                url     = url, 
                headers = self.headers, 
                data    = json.dumps(report_fields), 
                cookies = {"sid": self.session_id}
            )
            payload     = self.status_check(response)
            report_rows = payload['factMap']['T!T']['rows']
            self.mk1.logging.logger.info(f"(SalesforceAPI.get_report) Getting filtered report for `{report_id}` is successful !")
            return report_rows
        
        except Exception as e : 
            self.mk1.logging.logger.error(f"(SalesforceAPI.get_report) Getting filtered report for `{report_id}` failed : {e}")
            raise e
            
            

    
    def insert_sobject(self, 
            sobject        : str           = "",
            sobject_fields : Dict[str,Any] = {}
        ) -> str:
        """ Inserts a new SOBJECT
        
            Args
            ----
                :param: `sobject`        - The type of the existing SOBJECT. Options ~ {Contact, Account, User, Opportunity, Case}
                :param: `sobject_fields` - The salesforce dictionary with info for the existing SOBJECT (eg. name, type)
            
            Returns
            -------
                :returns: `payload` - The response dictionary
        """

        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + f"/services/data/v49.0/sobjects/{sobject}"
                                                                                                                                                             
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##                                                                                                                         
        try:
            response = requests.post(
                url     = url, 
                headers = self.headers, 
                data    = json.dumps(sobject_fields)
            )
            payload = self.status_check(response, has_payload = True, is_json = True) 
            self.puts_counter += 1  #v8.1
            print(f"(SalesforceAPI.insert_sobject) Inserting a new `{sobject}` SOBJECT was successful!")
            self.mk1.logging.logger.info(f"(SalesforceAPI.insert_sobject) Inserting a new `{sobject}` SOBJECT was successful!")
            return payload["id"]
        
        except Exception as e : 
            print(f"(SalesforceAPI.insert_sobject) Inserting a new `{sobject}` SOBJECT failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.insert_sobject) Inserting a new `{sobject}` SOBJECT failed : {e}")
            raise e
            
    def bulk_operation(
            self,
            sobject_data_df : pd.DataFrame,
            sobject         : str = 'Account', 
            sobject_id_type : str = 'Id',
            operation       : str = 'update',
            seconds         : int = 5
        ):
        """ Bulk Operation for SOBJECT """
        
        self.numberRecords = sobject_data_df.shape[0]
        
        job_id = self.csv_create_job(sobject, sobject_id_type, operation)
        self.csv_upload(job_id, sobject_data_df)
        self.csv_close_job(job_id)
        self.csv_check_job_state(job_id, seconds = seconds)
        report = self.get_job_reporting(job_id)
        return report
        
        
        
            
    def csv_create_job(
            self, 
            sobject         : str = 'Account', 
            sobject_id_type : str = 'Id',
            operation       : str = 'update'
        ):
        """ Create a Job ID for preparing the uploading of a csv file
        
            Args
            ----
                :param: `sobject`         -  The type of the existing SOBJECT. Options ~ {Contact, Account, User, Opportunity, Case}
                :param: `sobject_id_type` - The type of the id of the existing SOBJECT eg. 'Id'
                :param: `operation`       - The underlying operation for SOBJECT. Options ~ {update, insert,}
            
            Returns
            -------
                :returns: `job_id` - The `job_id` of the underlying operation
        """

        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + "/services/data/v54.0/jobs/ingest/"
                                            
        body = {
            "lineEnding"          : "LF",
            "object"              : sobject,
            "externalIdFieldName" : sobject_id_type,
            "contentType"         : "CSV",
            "operation"           : operation
        } 
        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##                                                                                                                         
        try:

            response = requests.post(
                url     = url, 
                headers = self.headers, 
                json    = body
            )
            payload = self.status_check(response, is_json = True)   
            job_id  = payload["id"]
            
            print(f"(SalesforceAPI.csv_create_job) Creating  a Job ID for uploading csv file was successful. Jod ID = {job_id}")
            self.mk1.logging.logger.info(f"(SalesforceAPI.csv_create_job) Creating  a Job ID for uploading csv file was successful. Jod ID = {job_id}")
            return job_id
        
        except Exception as e : 
            print(f"(SalesforceAPI.csv_create_job) Creating  a Job ID for uploading csv file failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.csv_create_job) Creating  a Job ID for uploading csv filefailed : {e}")
            raise e
            

        
    def csv_upload(
            self, 
            job_id          : str, 
            sobject_data_df : pd.DataFrame
        ) -> None:
        """ Create a Job ID for preparing the uploading of a csv file
        
            Args
            ----
                :param: `job_id`          -  The `job_id` of the underlying operation
                :param: `sobject_data_df` - The dataframe with all the SOBJECTs info

        """
        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url      = self.instance_url + f"/services/data/v54.0/jobs/ingest/{job_id}/batches/"
        fn_path  = self.df_to_csv(sobject_data_df)  
        headers  = self.headers.copy()
        headers["Content-Type"] = "text/csv; charset=utf-8"
        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##                   
        try :
            response = requests.put(
                url     = url, 
                headers = headers, 
                data    = fn_path
            )
            self.status_check(response, has_payload = False)

            print(f"(SalesforceAPI.csv_upload) Uploading the csv file (from dataframe) for the (Job ID = {job_id}) was successful")
            self.mk1.logging.logger.info(f"(SalesforceAPI.csv_upload) Uploading the csv file (from dataframe) for the (Job ID = {job_id}) was successful")
            return 
        
        except Exception as e : 
            print(f"(SalesforceAPI.csv_upload) Uploading the csv (file = `{fn_path}`) for the (Job ID = {job_id}) failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.csv_upload) Uploading the csv (file = `{fn_path}`) for the (Job ID = {job_id}) failed : {e}")
            raise e
            
            
    def csv_close_job(
            self, 
            job_id  : str, 
        ) -> None:
        """ Create a Job ID for preparing the uploading of a csv file
        
            Args
            ----
                :param: `job_id` -  The `job_id` of the underlying operation

        """
    

        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url  = self.instance_url + f"/services/data/v54.0/jobs/ingest/{job_id}/"
        body = {
            "state" : "UploadComplete" 
        }

        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##                   
        try : 
            response = requests.patch(
                url     = url, 
                headers = self.headers, 
                json    = body
            )
            self.status_check(response, has_payload = False)
          
            print(f"(SalesforceAPI.csv_close_job) Closing the (Job ID = {job_id}) was successful")
            self.mk1.logging.logger.info(f"(SalesforceAPI.csv_close_job) Closing the (Job ID = {job_id}) was successful was successful.")
            return 
        
        except Exception as e : 
            print(f"(SalesforceAPI.csv_close_job)  Closing the (Job ID = {job_id}) failed : {e}")
            self.mk1.logging.logger.error(f"(SalesforceAPI.csv_close_job) Closing the (Job ID = {job_id}) failed : {e}")
            raise e
            
    
   
            
    def csv_check_job_state(
            self, 
            job_id  : str, 
            seconds : int = 1
        ):
        """ Check until job status the job is finished
        
            Args
            ----
                :param: `job_id`  - The `job_id` of the underlying operation
                :param: `seconds` - The total waiting time.
        
        """

        while True:
            
            # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
            url = self.instance_url + f"/services/data/v54.0/jobs/ingest/{job_id}/"
            
            ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##
            try : 
                response = requests.get(
                    url     = url, 
                    headers = self.headers
                )
                payload               = self.status_check(response)
                job_state             = payload["state"]
                job_processed_records = payload["numberRecordsProcessed"]
                job_failed_records    = payload["numberRecordsFailed"]
                print(payload)
                time.sleep(seconds)
                
                
                if job_state in ['JobComplete', 'Aborted', 'Failed'] : 
                    print(f"(SalesforceAPI.csv_check_job_state) State: {job_state} was successful")
                    
                    self.mk1.logging.logger.info(f"(SalesforceAPI.csv_check_job_state) State: {job_state} was successful")
                    print(f"(SalesforceAPI.csv_check_job_state) State: {job_state}, Processed records: {job_processed_records}, Failed records: {job_failed_records}) was successful")
                    self.mk1.logging.logger.info(f"(SalesforceAPI.csv_check_job_state) State: {job_state}, Processed records: {job_processed_records}, Failed records: {job_failed_records}) was successful")
                    break

                else : 
                    print(f"(SalesforceAPI.csv_check_job_state) State: {job_state}, still processing ... {job_processed_records} (Failed : {job_failed_records}) out of {self.numberRecords} \n")
                    self.mk1.logging.logger.info(f"(SalesforceAPI.csv_check_job_state) State: {job_state}, still processing ... {job_processed_records} (Failed : {job_failed_records}) out of {self.numberRecords} \n ")
                    
            except Exception as e :
                print(f"(SalesforceAPI.csv_check_job_state) Retrieving the status for (Job ID = {job_id}) failed : {e}")
                self.mk1.logging.logger.error(f"(SalesforceAPI.csv_check_job_state)  Retrieving the status for (Job ID = {job_id}) failed : {e}")
                raise e
            

            
            
    def get_job_reporting(self, job_id : str) :
        # *-*-*-*-*-*- Creating the request -*-*-*-*-*-* ##
        url = self.instance_url + f"/services/data/v54.0/jobs/ingest/{job_id}/"
        payload = pd.DataFrame()
        
        
        ## *-*-*-*-*-*- Requesting -*-*-*-*-*-* ##                                                                                                                         
        try:
            
            
            ## *-*-*-*-*-*- [successfulResults] Requesting -*-*-*-*-*-* ##   
            print(url + "successfulResults/")
            response = requests.get(
                url     = url + "successfulResults/", 
                headers = self.headers, 
            )
            payload_success           = self.status_check(response, is_json = False) 
            payload_success           = self.csv_to_df(payload_success)
            payload_success["status"] = "Success"
            payload                   = pd.concat([payload, payload_success])
            
            ## *-*-*-*-*-*- [failedResults] Requesting -*-*-*-*-*-* ##
            response = requests.get(
                url     = url + "failedResults/", 
                headers = self.headers, 
            )
            payload_failed           = self.status_check(response, is_json = False)   
            payload_failed           = self.csv_to_df(payload_failed)
            payload_failed["status"] = "Failed"
            payload                  = pd.concat([payload,payload_failed])
            
            ## *-*-*-*-*-*- [unprocessedrecords] Requesting -*-*-*-*-*-* ##
            response = requests.get(
                url     = url + "unprocessedrecords/", 
                headers = self.headers, 
            )
            payload_unprocessed           = self.status_check(response, is_json = False)   
            payload_unprocessed           = self.csv_to_df(payload_unprocessed)
            payload_unprocessed["status"] = "Unprocessed"
            payload                       = pd.concat([payload,payload_unprocessed])
            
            self.mk1.logging.logger.info(f"(SalesforceAPI.get_job_reporting) Getting the report results for (Job ID = {job_id}) was successful")
            return payload
            
        except Exception as e : 
            self.mk1.logging.logger.error(f"(SalesforceAP.get_job_reporting) Getting the report results for (Job ID = {job_id}) failed : {e}")
            raise e

    
    

