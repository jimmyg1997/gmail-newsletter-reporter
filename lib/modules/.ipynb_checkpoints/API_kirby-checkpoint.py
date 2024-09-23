#!/usr/bin/env python3

"""
    [*] Description : Py3 wrapper for Kirby API. City Setup required documents automation
    [*] Author      : dimitrios.georgiou@uber.com | Original Author :  tetianab@uber.com
    [*] Date     : Oct 21, 2020
    [*] Links    : 
        - Tutorial : https://engwiki.uberinternal.com/display/KIRBY/Kirby+Ingestion+API
"""

import pandas as pd
import requests 
import json
import time

from typing import Callable, Dict, Generic, Optional, Set, Tuple, TypeVar, Deque, List


class KirbyAPI(object):
    
    """
    Access to HIVE tables through kirby ingestions. Currently supporting the following operations

    [GET]
    1. `get_schema`
    2. `get_table`
    3. `get_sink`
    4. `get_source`
    5. `get_ingestion_job_config`
    6. `get_feed`
    7. `get_multipart_form_data`
    8. `verify_job`
    
    
    [POST]
    1. `upload_to_hive`
    
    

    """
    def __init__(self, mk1):
        
        # MarkI
        self.mk1 = mk1     
        
        ## [Initialize] Attributes
        # [kirby_api]
        self.ldap                 = mk1.config.get("api_kirby","ldap")
        self.ingestion_mode       = mk1.config.get("api_kirby","ingestion_mode")
        self.ingestion_url        = mk1.config.get("api_kirby","ingestion_url")
        self.job_status_check_url = mk1.config.get("api_kirby","job_status_check_url")

        
        ## [Initialize] Objects
        self.dsw_headers = self.get_dsw_headers()
        self.datatypes   = self.get_datatypes()
        
        ## [Initialize] Client
        
    
    def __repr__(self):
        return f"Kirby object (ldap = {self.ldap})"
    
    
    #######################
    ##     UTILITIES     ##
    #######################
    
    def get_datatypes(self) : 
        datatypes = {
            'int64'          : 'Bigint',
            'float64'        : 'Double',
            'object'         : 'String',
            'bool'           : 'Boolean',
            'datetime64[ns]' : 'Timestamp'
        }
        
        return datatypes
    
    def get_dsw_headers(self) : 
        # authenticate
        dsw_headers = {
            'RPC-Service'         : "kirbycore",
            'X-Uber-Source'       : "dsw",
            'X-Auth-Params-Email' : f"{self.ldap}@uber.com"
        }
        
        return dsw_headers
        
        
    def get_schema(self, df : pd.DataFrame) -> Dict:
        # dynamically create schema from df datatypes
        fields = []
        columns_types = pd.DataFrame(df.dtypes)
        
        # match with accepted data types
        for i in columns_types.itertuples():
            fields.append({'name' : i[0], 'type' : self.datatypes[(str(i[1]))] })
        
        schema = { 
            "fields": fields 
        }
    
        return schema
        
    def get_table(self, table_name : str ):
        table = { 
            "tableName" : table_name,
            "secure"    : False # to ingest to dca1 change to True
        }
        
        return table 
    
    def get_sink(self, table_name : str):
        sink = {
            "type"   : "HIVE",
            "params" : json.dumps(self.get_table(table_name))
        }
        
        return sink 
    
    def get_source(self, df):
        source = {
            "type"   : "LOCALHOST",
            "format" : "CSV",
            "schema" : self.get_schema(df),
        }
        return source
    
    def get_ingestion_job_config(self):
        ingestion_job_config = {
            "writeMode"      : self.ingestion_mode,
            "processingMode" : "PERMISSIVE"
        }
        
        return ingestion_job_config 
    
    def get_feed(self, 
                 table_name : str, 
                 df         : pd.DataFrame) :
        feed = {
            "title"              : "kirby_feed_{}".format(self.ldap),
            "type"               : "ONETIME",
            "owner"              : self.ldap,
            "notificationEmails" : [ "{}@uber.com".format(self.ldap) ],
            "source"             : self.get_source(df),
            "sinks"              : [self.get_sink(table_name)],
            "ingestionJobConfig" : self.get_ingestion_job_config()
        }
        
        return feed 
    
    def get_multipart_form_data(self, 
                                table_name : str, 
                                df         : pd.DataFrame, 
                                file_path  : str) :
        
        print(table_name, file_path)
       
    
        #df.to_csv(file_path, index = False)
        
        csv_name = file_path.split("/")[-1]
        
        multipart_form_data = {
            "file": (csv_name, open(file_path, 'rb')),
            "feed": (None, json.dumps(self.get_feed(table_name, df)))
        }
        return multipart_form_data 
    
    
    def get_reporting(self, response, table_name) : 
        reporting =  {
                "Table_name"     : "kirby_external_data.{}".format(table_name),
                "Feed_ID"        : json.loads(response.text)['feedID'],
                "Job_ID"         : json.loads(response.text)['jobID'],
                "Status"         : str(json.loads(response.text)['status']),
                "Total rows"     : json.loads(response.text)['totalRows'],
                "Malformed rows" : json.loads(response.text)['malformedRows'],
                "Start time"     : str(json.loads(response.text)['startTime']),
                "End time"       : str(json.loads(response.text)['endTime']),
                "Error message"  : json.loads(response.text)['errorMessage'],
                "Duration"       : json.loads(response.text)['duration']
            } 
        
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Table Name = {}".format(reporting["Table_name"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Feed ID = {}".format(reporting["Feed_ID"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Job ID = {}".format(reporting["Job_ID"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Status = {}".format(reporting["Status"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Total Rows =  {}".format(reporting["Total rows"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Malformed Rows = {}".format(reporting["Malformed rows"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Start Time : {}".format(reporting["Start time"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) End Time : {}".format(reporting["End time"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Error Message : {}".format(reporting["Error message"]))
        self.mk1.logging.logger.info("(KirbyAPI.get_reporting) Duration : {}".format(reporting["Duration"]))
        
        

    
    def fix_columns(self, df : pd.DataFrame ) -> pd.DataFrame: 
        """Replacing columns names spaces and capital letters to Hive friendly format"""
        
        for column in df.columns :
            fixed_column = column.replace(" ", "_").lower()
            df = df.rename({column : fixed_column}, axis = 1)
            
        self.mk1.logging.logger.info("(KirbyAPI.fix_columns) Data columns are fixed.")
        return df
    
    
    def fix_data(self, df : pd.DataFrame, casting_map : Dict) : 

        for kind, columns in casting_map.items():
            try:
                
                if kind == "decimals" :
                    
                    for column in columns : 
                    
                        df[column] = df[column].fillna("0").astype(str).apply(lambda x: x.replace(',','')).astype(float)
                        
                elif kind == "percentages" : 
                    
                    for column in columns : 
                    
                        df[column] = df[column].fillna("0.00%").astype(str).apply(lambda x: x[:-1]).astype(float).apply(lambda x: x / 100)
                
                self.mk1.logging.logger.info("(KirbyAPI.fix_data) Data are fixed (imputing, datatypes).")
                return df
     
            except Exception as e:
                self.mk1.logging.logger.error("(KirbyAPI.fix_data) Data not fixed. {}".format(e))
                return e
            
            
                          
                
    def cast_to_hive_friendly_format(self, 
                                     df          : pd.DataFrame,
                                     casting_map : Dict) :
        
        for column, datatype in casting_map.items():
            try:
                
                if datatype == str : 
                    
                    df[column] = df[column].fillna("0").astype(datatype)
                    
                elif datatype == int :
                    
                    df[column] = df[column].replace("\\N",0).fillna(0).astype(datatype)
                    
                elif datatype == float :
                    
                    df[column] = df[column].replace("\\N",0.0).fillna(0.0).astype(datatype)
                    
                elif datatype == "datetime64[ns]" : 
                    
                    df[column] = pd.to_datetime(df[column])#, format = "%Y-%m-%d")
                    
                self.mk1.logging.logger.info("(KirbyAPI.cast_to_hive_friendly_format) Data are casted successfully.")
                return df
                    
            except Exception as e:
                self.mk1.logging.logger.error(f"(KirbyAPI.cast_to_hive_friendly_format) Data not casted : {e}")
                return e
            
            

 
    #-*-*-*-*-*-*-*-*-*-*-#
    #    GET / requests   #
    #-*-*-*-*-*-*-*-*-*-*-#

    def verify_job(self, 
                   job_id     : int, 
                   table_name : str,
                   time_sleep : int = 200) :
        
        time.sleep(time_sleep)
        
        try :
            response  = requests.get(self.job_status_check_url + str(job_id), headers = self.dsw_headers)
            reporting = self.get_reporting(response, table_name)
            print(reporting)
            self.mk1.logging.logger.info(f"(KirbyAPI.verify_job) Data are verified (job_id = {job_id})")
            return reporting
        
        except Exception as e:
            self.mk1.logging.logger.error(f"(KirbyAPI.verify_job) Data not verified. GET request failed: {e}")
            return e
        
        
        

    
    #-*-*-*-*-*-*-*-*-*-*-#
    #   POST / requests   #
    #-*-*-*-*-*-*-*-*-*-*-#
    
    def upload_to_hive(
            self, 
            table_name : str, 
            df         : pd.DataFrame, 
            file_path  : str
        ) -> int:
        
        """Upload csv file to as a kirby table to HIVE
            :param: `file_path` - eg.
                    "/mnt/cephfs/hadoop-compute/phoenix/dimitrios.georgiou/projects/apis/kirbyAPI/support_files/tax_data.csv"
            :param: `df`       - the dataframe we want to upload as a kirby table
            :param: `table_name` - The final kirby table name eg. `tax_data` -> kirby_external_data.tax_data
        
        """
        mltpf_data = self.get_multipart_form_data(table_name, df, file_path)
        
        
        try :
            response = requests.post(self.ingestion_url, headers = self.dsw_headers, files = mltpf_data)
            job_id   = json.loads(response.text)["data"]["jobID"]
            print(response.text)
            self.mk1.logging.logger.info(f"(KirbyAPI.upload_to_hive) Data are uploaded successfully (job_id = {job_id})")
            return job_id
    

        except Exception as e:
            self.mk1.logging.logger.error(f"(KirbyAPI.upload_to_hive) Data not uploaded. POST request failed: {e}")
            return e
        
        