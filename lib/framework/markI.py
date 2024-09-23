#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    [*] Description     : Py3 class for MarkI system design for all frameworks
    [*] Author          : dimitrios.georgiou@uber.com | Original Author :  Bruno
    [*] Date (created)  : Nov 4, 2022
    [*] Date (modified) : Jan 31, 2023
    [*] Links           :  
"""

# -*-*-*-*-*-*-*-*-*-*-* #
#     Basic Modules      #
# -*-*-*-*-*-*-*-*-*-*-* #
import os, json
import numpy  as np
import pandas as pd
from datetime import datetime
from typing   import Dict, Any, List, Tuple

# -*-*-*-*-*-*-*-*-*-*-*-* #
#     Framework Modules    #
# -*-*-*-*-*-*-*-*-*-*-*-* #
import dataset, logging
import logging.handlers as handlers
from configparser import RawConfigParser

class MkI(object):
    """ Builds the Singleton interface for all the contemplated features (treated as attributes)"""
    instance = None

    def __init__(self):
        pass

    @staticmethod
    def get_instance(**kwargs):
        if not MkI.instance:
            MkI.instance = MkI.__MkI(**kwargs)
        return MkI.instance

    class __MkI:
        def __init__(self, **kwargs):
            self.config  = self.get_config("./config/config.ini")
            self.dataset = self.get_dataset() if kwargs.get("_dataset", False) else None
            self.logging = self.get_logging() if kwargs.get("_logging", False) else None
            self.m3      = self.get_m3() if kwargs.get("_m3", False) else None

        # Initialize Methods
        def get_config(self, config_path):
            return Config(config_path).parser
        def get_dataset(self):
            return DataSet(self.config)
        def get_logging(self):
            return Logger(self.config)
        def get_m3(self):
            return M3(self.config)
        
        
## -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##

class Config(object):
    """ ConfigParser provides a basic configuration language which provides a structure similar to  Microsoft Windows .INI files """
    def __init__(self, config_path : str = "./config.ini"):
        self.parser = self.build_parser(config_path)
        
    def build_parser(self, config_path : str = "./config/config.ini") -> RawConfigParser:
        """ Creates the "parser" object from the "config.ini" file

            Args
            ----
               :param: `config_path` (:obj: `str`) - path to the "config.ini" file (default: file's root directory)

            Returns
            -------
               :retrurns: `parser` (:obj: Config)  - A ConfigParser object (with write/read on "config.ini")

        """
        
        parser = RawConfigParser() 
        try:
            #config_path = os.path.join(os.getcwd(), config_path)
            #print(os.getcwd(), config_path)
            
            with open(config_path) as f:
                parser.read_file(f)
            return parser
        
        except IOError as e:
            raise e
        
## -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##


class DataSet(object):
    """ Dataset provides a simple abstraction layer that removes most direct SQL statements without the necessity for a 
        full ORM model - essentially, databases can be used like a JSON file
    """
    def __init__(self, config_obj):
        self.config = config_obj
        self.db     = self.db_connect()

    def auto_search(self) -> Dict[str,str]:
        """ Searches for ".db" files within folders in this file's root directory
            
            Args
            ----
               :returns: `db_dict` (:obj: List[`str`, `str`]) - A Dictionary with database's path/name (.db extension)

        """
        db_dict = {
            "path" : None,  
            "name" : None
        }
    
        for root, dirs, files in os.walk("./"): # "os.walk" on this file's root folder (./)
            for file in files :                 # Loop files
                if file.endswith(".db"):        # Check for ".db" files
                    db_dict["path"], db_dict["name"] = root, file
        return db_dict

    def auto_update(
            self, 
            db_dict : Dict[str,str]
        ) -> None:
        """ Updates the database's path/name, found with "auto_search()", in the "config.ini" params

            Args
            ----
               :param: `db_dict`  (:obj: Dict[`str,`str])  - A Dictionary with database path/name (.db extension)
            
        """
        ## 1. Updating the "path"/"name" in "config.ini" file
        self.config.set('db', 'db_path', db_dict["path"])
        self.config.set('db', 'db_file', db_dict["name"])
        
        ## 2.Writing our configuration file to 'example.ini'
        with open("./config.ini", 'w') as config_file:
            self.config.write(config_file)
        return None

    def db_connect(self):
        """ Updates the database's path/name, found with "auto_search()", in the "config.ini" params

            Args
            ----
                :returns: `db_obj`   (:obj: `Dataset`) - A dataset database object
        """
        # Searching an existing database
        db_info = self.auto_search()
        # If database already exists...
        if db_info["name"] is not None:
            # Connect to existing database
            db_obj = dataset.connect(os.path.join("sqlite:///", db_info["path"], db_info["name"]))
            # Updating the "config.ini" file
            self.auto_update(db_info)
        else:
            # Create new database
            db_obj = dataset.connect(os.path.join("sqlite:///",
                                                  self.config.get("db","db_path"),
                                                  self.config.get("db","db_file")))
        return db_obj

    def db_disconnect(self):
        """ Disconnects from the database object stored in "self.db"

            Args
            ----  
        """
        # Disconnecting from the database
        self.db.executable.close()
        return None

    def db_create_table(self, table_name : str = "", pk_name : str = "", pk_str : str = ""):
        """ Creates a table with name and primary key (with type) in the "self.db" database object

            Args
            ----
                :param: `table_name`  (:obj: `str`)  - The name of the table being created
                :param: `pk_name`     (:obj: `str`)  - The name of the column to be used as primary key
                :param: `pk_str`      (:obj: `str`)  - The type of the column being used as primary key  
        """

        try:
            # Creating the table and commiting changes
            self.db.create_table(table_name, primary_id = pk_name, primary_type = self.get_pk_type(pk_str))
            self.db.commit()
        except:
            # Rolling changes back
            self.db.rollback()
        return None
    

    def db_delete_table(self, table_name : str = ""):
        """ Deletes a table (by its name) in the "self.db" database object

            Args
            ----
                :param: `table_name`  (:obj: `str`)  - The name of the table being deleted 
        """

        try:
            # Deleting the table and commiting changes
            self.db[table_name].drop()
            self.db.commit()
        except:
            # Rolling changes back
            self.db.rollback()
        return None
    
    
    

    def db_append_row(self, table_name : str = "", input_dict : Dict[str, str] = {}):
        """ Appends a single (1) row (through a dictionary) to the "self.db" database object

            Args
            ----
                :param: `table_name`  (:obj: `str`)         - The name of the table being deleted
                :param: `input_dict`  (:obj: Dict[str,str]) - A dictionary holding data to be appended (keys as columns, values as values)
        """
        try:
            # Inserting a row (through a dictionary) and commiting changes
            self.db[table_name].insert(input_dict)
            self.db.commit()
        except:
            # Rolling changes back
            self.db.rollback()
        return None

    def db_append_df(self, table_name : str = "", input_df : pd.DataFrame = None):
        """ Appends multiple rows (through a dataframe) to the "self.db" database object

            Args
            ----
                :param: `table_name`  (:obj: `str`)        - The name of the table being deleted
                :param: `input_df`    (:obj: pd.DataFrame) - The dataframe holding data to be appended (headers as columns, values as values)   
        """
        # Preparing the Dataframe
        df = input_df.to_dict(orient = "records")
        try:
            # Inserting a row (through df) and commiting changes
            self.db[table_name].insert_many(df)
            self.db.commit()
        except:
            # Rolling changes back
            self.db.rollback()
        return None

    def db_update(self, table_name : str = "", values_dict : Dict[str,str] = {}, col_filter : List[str] = []):
        """ Updates all rows filtered by the "col_filter" list with key/values specified by "values_dict"

            Args
            ----
                :param: `table_name`  (:obj: `str`)          - The name of the table being deleted
                :param: `values_dict` (:obj:  Dict[str,str]) - The dictionary with values for "col_filter" and additional columns to be updated
                :param: `col_filter`  (:obj:  Dict[str,str]) - The list with columns' names used to filter rows to be updated (value must be inputed in "values_dict")


            Returns
            -------
                None   
        """
        try:
            # Updating rows (based on "col_filter" and "values_dict") and commiting changes
            self.db[table_name].update(row = values_dict, keys = col_filter)
            self.db.commit()
        except:
            # Rolling changes back
            self.db.rollback()
        return None
    
    
    

    def db_upsert(self, table_name : str = "", values_dict : Dict[str,str] = {}, col_filter : List[str] = []):
        """ Updates all rows (present in "table_name") filtered by "col_filter" with key/values specified by "values_dict". Inserts "values_dict" as a new row, 
            otherwise (columns not mentioned in "values_dict" get None as value)

            Args
            ----
                :param: `table_name`  (:obj: `str`)          - The name of the table being deleted
                :param: `values_dict` (:obj:  Dict[str,str]) - The dictionary with values for "col_filter" and additional columns to be upserted
                :param: `col_filter`  (:obj:  Dict[str,str]) - The list with columns' names used to filter rows to be upserted (value must be inputed in "values_dict") 
        """
            
        try:
            # Updating rows (based on "col_filter" and "values_dict") and commiting changes
            self.db[table_name].upsert(row = values_dict, keys = col_filter)
            self.db.commit()
        except:
            # Rolling changes back
            self.db.rollback()
        return None
    
    
    

    def db_delete(self, table_name : str = "", filters_dict : Dict[str,str] = {}):
        """ Deletes rows by filters (conditions are joined with ANDs statements)

            Args
            ----
                :param: `table_name`  (:obj: `str`)           - The name of the table being deleted
                :param: `filters_dict` (:obj:  Dict[str,str]) - The dictionary with filter information. Rows respecting the thresholds in the f 
        """

        try:
            # Deleting rows (based on "filters_dict") and commiting changes
            self.db[table_name].delete(**filters_dict)
            self.db.commit()
        except:
            # Rolling changes back
            self.db.rollback()
        return None

    def db_query(self, query_str : str = "") -> pd.DataFrame:
        """ Queries against the "self.db" database object

            Args
            ----
                :param: `query_str`  (:obj: `str`) - The complete query string
               :returns: `df`  (:obj: pd.DataFrame) - Dataframe containing all the rows from the query result in the local db
        """
        try:
            # Querying the db and commiting changes
            result = self.db.query(query_str)
            self.db.commit()
            # Pushing "result" to a Dataframe
            df = pd.DataFrame(data=list(result))
            return df
        except:
            # Rolling changes back
            self.db.rollback()
        return None
    
    
    

    def get_pk_type(self, pk_str : str):
        """ Translates pre-defined strings to SQLite data types, used on "db_create_table"s "primary_type" parameter

            Args
            ----
                :param: `pk_type`  (:obj: `str`) - The String representation of data type. Any of:
                           - "b_int"    : for big integers (returns db.types.biginteger)
                           - "int"      : for integers (returns db.types.integer)
                           - "s_int"    : for small integers (returns db.types.smallinteger)
                           - "float"    : for floats (returns db.types.float)
                           - "str"      : for fixed-sized strings (returns db.types.string)
                           - "txt"      : for variable-sized strings (returns db.types.text)
                           - "bool"     : for booleans (returns db.types.boolean)
                           - "date"     : for datetime.date() objects (returns db.types.date)
                           - "datetime" : for datetime.datetime() objects (returns db.types.datetime)

                :returns: SQLite data type obj
        """
        # Translating "pk_type" into a SQLite data type object
        if pk_str.lower() == "b_int":
            return self.db.types.biginteger
        elif pk_str.lower() == "int":
            return self.db.types.integer
        elif pk_str.lower() == "s_int":
            return self.db.types.smallinteger
        elif pk_str.lower() == "float":
            return self.db.types.float
        elif pk_str.lower() == "str":
            return self.db.types.string
        elif pk_str.lower() == "txt":
            return self.db.types.string
        elif pk_str.lower() == "bool":
            return self.db.types.boolean
        elif pk_str.lower() == "date":
            return self.db.types.date
        elif pk_str.lower() == "datetime":
            return self.db.types.datetime
        else:
            return None

    def get_tables(self) -> List[str]:
        """ Lists all existing tables in the database

            Args
            ----
                None

            Returns
            -------
                :returns: The list with existing tables' names in the database
        """
        return self.db.tables

    def get_cols(self, table_name : str = ""):
        """ Lists all existing columns in a table

            Args
            ----
                :param: `table_name`  (:obj: `str`) - The name of the table containing the columns
                :returns: The list with existing columns in "table_name"
        """
        return self.db[table_name].columns

    def get_rows(self, table_name : str = ""):
        """
            Gets the total rows in a table

            Args
            ----
                `table_name`  (:obj: `str`) - The name of the table containing the columns
                :returns: The total rows (integer) in the "table_name"
        """
        return len(self.db[table_name])

    def get_unique(self, table_name : str = "", col_name : str = ""):
        """ Gets unique values for a column in a table

            Args
            ----
                :param: `table_name`  (:obj: `str`) - The name of the table containing the column
                :param: `col_name`  (:obj: `str`)   - The name of the column to be analyzed
                :returns: A list with unique values in "col_name"
        """
        return [list(each.values())[0] for each in self.db[table_name].distinct(col_name)]

## -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##

class Logger(object):
    """Logging provides a flexible event logging system for applications and libraries"""
    def __init__(self, config_obj):
        self.config = config_obj
        
        ## *-*-*-*-*-*-*-* Initializing attributes *-*-*-*-*-*-*-* ##
        self.level       = self.config.get("logger","level")
        self.fmt         = self.config.get("logger","format")
        self.datefmt     = self.config.get("logger","asctime")
        self.log_fn_path = self.config.get("logger","fn_path")
        self.log_name    = self.config.get("logger","name")
        self.app_oname   = self.config.get("app","official_name")
        self.app_name    = self.config.get("app","name")
        
        ## *-*-*-*-*-*-*-* Initializing objects *-*-*-*-*-*-*-* ##
        self.formatter = self.set_formatter()
        self.handler   = self.set_handler()
        self.logger    = self.start_logger()

    def set_formatter(self):
        """ Instantiates the Formatter class and sets the messages/dates formats

            Args
            ----
               :returns: Formatter class instance with format from "self.format"
        """
        return logging.Formatter(
            fmt     = self.fmt, 
            datefmt = self.datefmt
        )

    def set_handler(self):
        """ Instantiates the FileHandler class, sets it as a handler, sets its level and receives the Formatter instance ("self.formatter")

            Args
            ----
                :returns: FileHandler class instance with "self.formatter" as formatter
        """
        # Creating a handler
        handler = logging.FileHandler(self.log_fn_path)
        # Adding the formatter to the handler
        handler.setFormatter(self.formatter)
        return handler

    def start_logger(self):
        """ Instantiates a logger and receives a handler("self.handler")

            Args
            ----
                :returns: Customized logger class with a INFO message to states the beginning of a session
        """
        # Creating and storing a new logger
        logger = logging.getLogger(self.log_name)
        # Setting the level on the handler
        logger.setLevel(self.level)
        # Adding the handler to "my_logger"
        logger.addHandler(self.handler)
        # Starting the session
        logger.info(f"-------------------------------------- {self.app_oname} ({self.app_name}) Started ..")
        return logger

## -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##


class M3(object):
    """M3 provides an easy way to store and query metrics, allowing quick insights into processes they are emitted from."""
    def __init__(self, config_obj):
        self.config       = config_obj
        self.off_token    = self.get_off_token() # https://ugrafana.uberinternal.com/oidauth/offline
        self.service_tag  = self.config.get("m3","service_tag")
        self.env_tag      = self.config.get("m3","env_tag")
        self.metric_tag   = self.config.get("m3","metric_tag")
        self.push_client  = self.auth_push_client()
        self.read_client  = self.auth_read_client()
        self.created_at   = self.get_now_secs()
        
        
    # -*-*-*-*-*-*-*-*- #
    #     UTILITIES     #
    # -*-*-*-*-*-*-*-*- #
    def get_now_secs(self) -> Dict[str,Any]:
        """ Gets push client's current time (ms/ns) and returns as seconds (epochs)

            Args
            ----
                 :returns: A dictionary with "now" as epochs/timestamp
        """
        if self.push_client.emit_timing_in_ns : now_s = self.ns_to_s(self.push_client.current_nano_time())
        else                                  : now_s = self.ms_to_s(self.push_client.current_micro_time())
            
        return {
            "epochs"    : now_s, 
            "timestamp" : self.s_to_datetime(now_s)
        }

    def convert_to_secs(self, x : int, x_type = "") -> int:
        """ Converts X to seconds

            Args
            ----
                :param: `x`      (:obj: `int`) - The time in {miliseconds, nanoseconds}
                :param: `x_type` (:obj: `str`) - The type of the X
                 :returns: Time in seconds (integers)
        """
        
        if x_type == "ns"   : return int(round(ns/1000000000.0,0))
        elif x_type == "ms" : return int(round(ms/1000000.0,0))
        
    
    def secs_to_datetime(self, s : int):
        """ Converts seconds to a timestamp string

            Args
            ----
                :param: `s` (:obj: `int`) - time in seconds
                :returns: timestamp string
        """
        return datetime.fromtimestamp(s).strftime("%Y-%m-%d %H:%M:%S")
        
        
    # -*-*-*-*-*-*-*-*- #
    #       Client      #
    # -*-*-*-*-*-*-*-*- #

    def get_off_token(self):
        """ Reads Grafana's offline token from the "config.ini" file

            Args
            ----
                :returns: Grafana's offline token string
        """
        # Reading the "grafana_token.json"
        with open(self.config.get("m3","token_path")) as json_file:
            off_token = json.load(json_file)["token"]
        return off_token


   
    
    # -*-*-*-*-*-*-*-*- #
    #    PUSH Client    #
    # -*-*-*-*-*-*-*-*- #
    def auth_push_client(self):
        """ Authenticates and instantiates M3's PUSH client 

            Args
            ----
                :returns: M3's push client object
        """
        return M3Client.M3(
            application_identifier = self.service_tag, # service emitting the metrics
            environment            = self.env_tag,     # environment tags are being emitted from
            include_host           = True              # True: include the host tag with socket.gethostname() set
        )            
    
    def get_host(self):
        """ Returns the session host

            Args
            ----
                :returns: session host string
        """
        return self.push_client.host
    
    def push_counter(self, key_ : str, n_ : int =  1, tags_ : Dict[str,str] = {}):
        """ Uploads a timing metric via the push client

            Args
            ----
                :param: `key_`   (:obj: `str`)             - The metric tag
                :param: `n_`     (:obj: `int`)             - The counter value
                :param: `key_`   (:obj: Dict[`str`,`str`]) - The additional tags dictionary
        """
        self.push_client.count(key = key_, n = n_, tags = tags_)
        return None

    def push_gauge(self, key_ : str, value_ : int, tags_ : Dict[str,str] = {}):
        """  Uploads a timing metric via the push client

            Args
            ----
                :param: `key_`   (:obj: `str`)             - The metric tag
                :param: `value_` (:obj: `int`)             - The gauge value
                :param: `key_`   (:obj: Dict[`str`,`str`]) - The additional tags dictionary
        """
        self.push_client.gauge(
            key   = key_, 
            value = value_, 
            tags  = tags_
        )
        return None

    def push_timing(self, key_ : str, duration_ : int, tags_ : Dict[str,str] = {}):
        """ Uploads a timing metric via the push client

            Args
            ----
                :param: `key_`      (:obj: `str`)             - The metric tag
                :param: `duration_` (:obj: `int`)             - The metric tag
                :param: `key_`      (:obj: Dict[`str`,`str`]) - The additional tags dictionary
        """
        self.push_client.gauge(
            key      = key_, 
            duration = duration_, 
            tags     = tags_
        )
        return None
    
    # -*-*-*-*-*-*-*-*- #
    #    READ Client    #
    # -*-*-*-*-*-*-*-*- #
    def auth_read_client(self):
        """ Authenticates and instantiates M3's READ client 

            Args
            ----
                :returns: M3's read client object
        """
        return ReadM3Client(auth_key = self.off_token)

    def query(self, query_str : str, from_ : int, until_ : int, tries : int = 3) -> Dict[str,int]:
        """ Queries M3 via the read client

            Args
            ----
                :param: `query_str` (:obj: `str`)  - The query as a string
                :param: `from_`     (:obj: `int`)  - Start epoch value (in secs)
                :param: `until_`    (:obj: `int`)  - End epoch value (in secs)
                :param: `tries`     (:obj: `int`)  - Attempts for query to run
                :returns: `df` (:obj: pd.DataFrame) - A Dictionary with "dc", "metric" (name), "service" (name), "type"and "data" (df with epochs / dt_str / values)
        
        """
        # Querying
        results = self.read_client.fetch_query(
            query           = query_str, 
            from_timestamp  = from_, 
            until_timestamp = until_, 
            retries         = tries
        )
        
        # Storing "datapoints" in a dataframe
        col_name = results[0]["tags"]["type"]
        df = pd.DataFrame(columns = ["epochs_s", "dt_str", col_name])
        
        for pair in results[0]["datapoints"]:
            df_ = {
                "epochs_s" : pair[1], 
                "dt_str"  : self.s_to_datetime(pair[1]), 
                col_name  : pair[0]
            }
            df = df.append(df_ , ignore_index = True)
            
        # Type casting "None" strings into NULLs
        df = df.replace(np.nan, 0)
        
        # Building the final dictionary
        return {
                "dc"      : results[0]["tags"]["dc"],
                "metric"  : results[0]["tags"]["name"],
                "service" : results[0]["tags"]["service"],
                "type"    : results[0]["tags"]["type"],
                "data"    : df
        }
 