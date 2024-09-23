#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""
    [*] Description     : A simple wrapper module for Queryrunner API. Supports both (1) Atlantis queries at Hive (2) Neutrino queries at Eva Pinot
    [*] Original Author : brianr@suber.com
    [*] Author          : dimitrios.georgiou@uber.com 
    [*] Date (created)  : Apr, 2021
    [*] Date (modified) : Jan 31, 2023
    [*] Links       :  
        1. Module (this script) - https://workbench.uberinternal.com/file/62420136-629a-4026-af30-aed298518acd
        2. Runbook - https://workbench.uberinternal.com/file/c20e3ade-9af0-454b-ba1e-823c0ca500ef
        3. Vanilla queryrunner_client guide  - https://workbench.uberinternal.com/file/2ca7d488-731d-47a8-a8ab-97e0ea123131
        4. Vanilla queryrunner_client documentation -  https://eng.uberinternal.com/docs/queryrunner_client/queryrunner_client.html
        5. Presto github repo : https://github.com/prestodb/presto-python-client
"""
# -*-*-*-*-*-*-*-*-*-*-* #
#     Basic Modules      #
# -*-*-*-*-*-*-*-*-*-*-* #
import json
import itertools
import pandas as pd
import queryrunner_client.lib.exceptions as qr_exceptions
from retry import retry
from typing import (
    Callable,
    Dict,
    Generic,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Deque,
    List,
    Any,
)

# -*-*-*-*-*-*-*-*-*-*-*-* #
#   Third-Party Modules    #
# -*-*-*-*-*-*-*-*-*-*-*-* #

from queryrunner_client import (
    Client, 
    QueryRunnerException
)
from concurrent.futures import (
    ThreadPoolExecutor, 
    as_completed
)


class QueryAPI:
    DATABASES = [
            "hive", 
            "pinot"
        ]
    DATABASES_DICT = {
        "hive": "atlantis", 
        "pinot": "neutrino"
    }
    DATACENTERS = [
        "pxh2", 
        "dca1"
    ]
    
    def __init__(self, mk1):
        # System Design
        self.mk1 = mk1

    # Client
    def build_client(self, is_interactive: bool = False):
        client = Client(
            user_email=self.admin_email,
            consumer_name=self.consumer_name,
            interactive=is_interactive,
        )
        return client

    # Utilities
    @property
    def __repr__(self):
        """Returns a string representation of the QueryrunnerClient object including the version info."""
        return f"(QueryAPI) (user_email = {self.email}; queryrunner version {queryrunner_client.__version__ }"

    @property
    def get_datasources(self):
        """Returns a list of all available datasources."""
        return self.client.list_datasources()

    @staticmethod
    def print_pretty_dict(d: Dict[Any, Any]):
        """Print a dictionary in a nice fancy intend way json()"""
        print(json.dumps(d, indent=4))

    @staticmethod
    def readable_time(seconds) -> str:
        """Makes seconds into a readable time string."""
        m, s = divmod(seconds, 60)
        return f"{m} minutes and {s} seconds"

    @staticmethod
    def param_string_limit(param_dict, max_length=100) -> str:
        """Converts parameter dict to string with ... if it's too long"""
        if len(str(param_dict)) > max_length:
            return str(param_dict)[: max_length - 3] + "..."
        else:
            return str(param_dict)

    def generate_parameters_combinations(
        self, parameters_list: List[List[Any]], parameters_names=List[str]
    ) -> List[Dict[str, Any]]:
        """Generate all possible combinations for a variable number of parameters and its values

        Args
        ------
            :param: `parameters_list`  - A list with all the parameter values
            :param: `parameters_names` - A list with all the parameter names

        Returns
        ------
            :returns: `parameters_combs`  - A list with all possible parameter dictionaries combinations

        """

        parameters_combs = list(itertools.product(*parameters_list))
        num_parameters = len(parameters_list)
        num_values = sum([len(param) for param in parameters_list])
        num_combs = len(parameters_combs)

        parameters_combs = [
            {parameters_names[idx]: param[idx] for idx in range(num_parameters)}
            for param in parameters_combs
        ]

        self.mk1.logging.logger.info(
            f"(QueryAPI.generate_parameters_combinations) [Success] From {num_parameters} parameters with a total of {num_values} values,\
                                    {num_combs} parameter dictionaries were generated"
        )

        return parameters_combs


# ----------------------------- 1. (Query) NEUTRINO ----------------------------------------- #

class QueryNeutrinoAPI(QueryAPI):
    """ API wrapper for [Atlantis] queries in the `Eva Pinot` database """
    def __init__(self, mk1):
        ## *-*-*- (a) Initializing GoogleAPI (Parent class) -*-*-* ##
        QueryAPI.__init__(self, mk1)
        
        ## *-*-*- (b) Initializing Attributes -*-*-* ##
        self.admin_email   = str(mk1.config.get("admin","ldap"))    
        self.consumer_name = str(mk1.config.get("admin","consumer_name"))    
        
        ## *-*-*- (c) Initializing Attributes -*-*-* ##                    
        self.client = self.build_client()
        

    def run_queries_parallel(
        self,
        report_id: str,
        parameters_list: List[List[Any]] = [],
        parameters_names: List[str] = [],
        parameters_combs: List[Dict[str, Any]] = None,
        max_workers: int = 6,
    ) -> Tuple[Dict[Tuple[Any], pd.DataFrame], pd.DataFrame]:
        """Wrapper for queryrunner_client.Client.execute()

        Args
        ----
            :param: `report_id` - String representation of the report id of the underlying SQL query
            :param: `parameters_list` -  A list of list. Each sublist contains the values of a specific parameter
            :param: `parameters_names`-  A list with all the parameter names
            :param: `parameters_combs`-  A list with parameter dictionaries combinations. If None we calculate all the possible combinations
            :param: `max_workers` -  The maximum number of workers so that the queries are executed in parallel
            
            :returns: `data_dict`- A dict with all the dataframes. Each dataframe is a query execution result
            :returns: `metadata` - A dataframe with all the metadata dataframes. Each dataframe is a the metadata information/analytics for a query execution


        """

        data_dict = {}

        ## *-*-*-*-*-*-*-*-*-*-*-*- Generate Parameters Combinations  -*-*-*-*-*-*-*-*-*-*-*-* ##
        parameters_combs = (
            self.generate_parameters_combinations(parameters_list, parameters_names)
            if not parameters_combs
            else parameters_combs
        )
        metadata = pd.DataFrame(
            index=[tuple(params.values()) for params in parameters_combs]
        )

        ## *-*-*-*-*-*-*-*-*-*-*-*- Execution  -*-*-*-*-*-*-*-*-*-*-*-* ##
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            ## 1. Set futures as dict so that you have access to params (through its values)
            futures = {
                executor.submit(self.run_query, report_id, params): params
                for params in parameters_combs
            }

            ## 2. Process task results as they are available
            for f in as_completed(futures.keys()):
                try:
                    data, _ = f.result()
                    key = tuple(futures[f].values())
                    data_dict[key] = data
                    metadata.loc[key, "Exists"] = not data.empty
                    metadata.loc[key, "# Rows"] = int(data.shape[0])

                except Exception as e:
                    self.mk1.logging.logger.error(
                        f"(QueryNeutrinoAPI.run_queries_parallel) Skipping ...  {e}"
                    )

        self.mk1.logging.logger.info(
            "(QueryNeutrinoAPI.run_queries_parallel) Excuted Successfully !}"
        )
        return data_dict, metadata

    def run_query_parallel(
        self, report_id: str, parameters: Dict[str, Any], max_workers: int = 6
    ):
        pass

    def run_query(
        self,
        report_id: str,
        parameters: Dict[str, Any],
        datacenter: str = "phx2",
        timeout: int = 600,
        attempts: int = 1,
        sleep: int = 10,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Wrapper for queryrunner_client.Client.execute()

        Args
        ----
            :param: `report_id`  - String representation of the report id of the underlying SQL query
            :param: `parameters` - Dictionary of string keys and values for queryrunner
            :param: `datacenter` - 'dca1' or 'phx2'
            :param: `timeout`    - Time in seconds to run query before indicating the query has failed (max: 1800)
            :param: `attempts`   - Number of retries if it fails
            :param: `sleep`      - Time, in seconds, for it to sleep between attempts
            :param: `headers`    - Boolean, indicating if the result datafrae will have heaers or niot !
            
            :returns: `data`     - A dataframe of the query execution result
            :returns: `metadata` - A dict with all the metadata of the query execution

        Notes
        -----
        * EDITS : datacenter `dca1` is deprecated

        """

        for current_attempt in range(attempts):
            self.mk1.logging.logger.info(
                f"(QueryNeutrinoAPI.run_query) Attempt {str(current_attempt + 1)} out of {str(attempts)}"
            )
            self.mk1.logging.logger.info(
                f"(QueryNeutrinoAPI.run_query) [Report ID]  {report_id} | [Params] {parameters}"
            )

            try:
                # ------------------------------------- 1. Load Data -------------------------------------- #
                ## 1.1 Execute the query with the current datacenter

                result = self.client.execute_report(
                    report_id=report_id,
                    parameters=parameters,
                    datacenter=datacenter,
                    timeout=timeout,
                    pii=True,
                    cancel_if_timeout=True,
                )

                data = pd.DataFrame(result.load_data())

                """
                EDIT : `dca1` is DEPRECATED
                1.2 If the current datacenter is busy, try again with another datacenter
                
                if len(data) == 0:
                    result = self.client.execute_report(
                                report_id         = report_id, 
                                parameters        = parameters,
                                datacenter        = "dca1" if datacenter == "phx2" else "phx2",
                                timeout           = timeout,
                                pii               = True,
                                cancel_if_timeout = True
                    )
                    data = pd.DataFrame(result.load_data())
                """

                # ------------------------------------- 2. Load Metadata -------------------------------------- #
                # 2. Determine if it succeeded (completed_success or finished_success in metadata status)

                metadata = result.metadata

                if not metadata["is_error"]:
                    num_rows = data.shape[0]  # metadata["row_count"]
                    self.mk1.logging.logger.info(
                        f"(QueryNeutrinoAPI.run_query)  [Success] Rows: {num_rows}"
                    )
                    return data, metadata

                else:
                    e = (
                        metadata["error_message"]
                        if metadata["error_message"] != ""
                        else "Error not available."
                    )
                    self.mk1.logging.logger.error(
                        f"(QueryNeutrinoAPI.run_query) [Failed]  Query could not run! Error message: {e}. Sleeping for {str(sleep)} s before retrying"
                    )
                    time.sleep(sleep)

            except QueryRunnerException as e:
                self.mk1.logging.logger.info(
                    f"(QueryNeutrinoAPI.run_query) [Failed] Query could not run! Check query parameters and try again : {e}"
                )
                raise e


# ----------------------------- 2. (Query) ATLANTIS ----------------------------------------- #

class QueryAtlantisAPI(QueryAPI):
    """ API wrapper for [Atlantis] queries in the `Hive` database """
    def __init__(self, mk1):
        ## *-*-*- (a) Initializing GoogleAPI (Parent class) -*-*-* ##
        QueryAPI.__init__(self, mk1)
        
        ## *-*-*- (b) Initializing Attributes -*-*-* ##
        self.admin_email   = str(mk1.config.get("admin","ldap"))    
        self.consumer_name = str(mk1.config.get("admin","consumer_name"))    
        
        ## *-*-*- (c) Initializing Attributes -*-*-* ##                    
        self.client = self.build_client()


    def run_queries_parallel(
        self,
        report_id: str,
        parameters_list: List[List[Any]] = [],
        parameters_names: List[str] = [],
        parameters_combs: List[Dict[str, Any]] = None,
        max_workers: int = 6,
    ) -> Tuple[Dict[Tuple[Any], pd.DataFrame], pd.DataFrame]:
        """Wrapper for queryrunner_client.Client.execute()

        Args
        ----
            :param: `report_id`       - String representation of the report id of the underlying SQL query
            :param: `parameters_list` -  A list of list. Each sublist contains the values of a specific parameter
            :param: `parameters_names`-  A list with all the parameter names
            :param: `parameters_combs`-  A list with parameter dictionaries combinations. If None we calculate all the possible combinations
            :param: `max_workers`     -  The maximum number of workers so that the queries are executed in parallel
            :returns: `data_dict`  - A dict with all the dataframes. Each dataframe is a query execution result
            :returns: `metadata`  - A dataframe with all the metadata dataframes. Each dataframe is a the metadata information/analytics for a query execution

        Notes
        -----


        """

        data_dict = {}

        ## *-*-*-*-*-*-*-*-*-*-*-*- Generate Parameters Combinations  -*-*-*-*-*-*-*-*-*-*-*-* ##
        parameters_combs = (
            self.generate_parameters_combinations(parameters_list, parameters_names)
            if not parameters_combs
            else parameters_combs
        )
        metadata = pd.DataFrame(
            index=[tuple(params.values()) for params in parameters_combs]
        )

        ## *-*-*-*-*-*-*-*-*-*-*-*- Execution  -*-*-*-*-*-*-*-*-*-*-*-* ##
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            ## 1. Set futures as dict so that you have access to params (through its values)
            futures = {
                executor.submit(self.run_query, report_id, params): params
                for params in parameters_combs
            }

            ## 2. Process task results as they are available
            for f in as_completed(futures.keys()):
                try:
                    data, _ = f.result()
                    key = tuple(futures[f].values())
                    data_dict[key] = data
                    metadata.loc[key, "Exists"] = not data.empty
                    metadata.loc[key, "# Rows"] = int(data.shape[0])

                except Exception as e:
                    self.mk1.logging.logger.error(
                        f"(QueryAtlantisAPI.run_queries_parallel) Skipping ...  {e}"
                    )

        self.mk1.logging.logger.info(
            "(QueryAtlantisAPI.run_queries_parallel) Excuted Successfully !}"
        )
        return data_dict, metadata

    @retry(exceptions=(qr_exceptions.ResultError, qr_exceptions.ServiceError,
                       qr_exceptions.StreamingError), tries=10, delay=5, jitter=(0, 5))
    def run_query(
        self,
        report_id: str,
        parameters: Dict[str, Any],
        datacenter: str = "phx2",
        timeout: int = 600,
        headers: bool = True,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Wrapper for queryrunner_client.Client.execute()

        Args
        ----
            :param: `report_id`  - String representation of the report id of the underlying SQL query
            :param: `parameters` - Dictionary of string keys and values for queryrunner
            :param: `database`   - 'hive' or 'pinot'(real-time)
            :param: `datacenter` - 'dca1' or 'phx2'
            :param: `timeout`    - Time in seconds to run query before indicating the query has failed (max: 1800)
            :param: `attempts`   - Number of retries if it fails
            :param: `sleep`      - Time, in seconds, for it to sleep between attempts
            :param: `headers`    - Boolean, indicating if the result datafrae will have heaers or niot !
            :returns: `data`     - A dataframe of the query execution
            :returns: `metadata` - A dict with all the metadata of the query execution

        Notes
        -----
        * EDITS : datacenter `dca1` is deprecated

        """
        self.mk1.logging.logger.info(
            f"(QueryAltantisAPI.run_query) [Report ID]  {report_id} | [Params] {parameters}"
        )

        # Map of error messages for exception handling
        LOG_MESSAGES = {
            "ResultError": "(QueryAltantisAPI.run_query) error when reading to pandas: {e}",
            "PollTimeoutError": "(QueryAltantisAPI.run_query) query polling timeout: {e}",
            "StreamingError": "(QueryAltantisAPI.run_query) StreamingError: {e}",
            "ServiceError": "(QueryAltantisAPI.run_query) ServiceError. Happens when cerberus is off: {e}",
            "QueryRunnerException": "(QueryAltantisAPI.run_query) QueryRunnerException: {e}",
            "Unhandled": "(QueryAltantisAPI.run_query) Unhandled error: {e}"
        }

        # ------------------------------------- 1. Load Data -------------------------------------- #
        ## 1.1 Execute the query with the current datacenter
        try:
            result = self.client.execute_report(
                report_id=report_id,
                parameters=parameters,
                datacenter=datacenter,
                timeout=timeout,
                pii=True,
                cancel_if_timeout=True,
            )

            data = result.to_pandas(with_headers=headers)
            
        # Most of the errors we handle with retry inherit from QueryRunnerException
        # To avoid writing a bunch of excepts, we check for type of exception using if
        except Exception as e:
            if (isinstance(e, QueryRunnerException)
                or isinstance(e, qr_exceptions.ServiceError)):
                # This pulls log message based on exception class
                msg = LOG_MESSAGES[e.__class__.__name__].format(e=e)    
            else:
                msg = LOG_MESSAGES["Unhandled"].format(e=e)
            self.mk1.logging.logger.error(msg)
            # For exceptions included in @retry, this raise triggers the decorator
            raise e
        """
        EDIT : `dca1` is DEPRECATED
        1.2 If the current datacenter is busy, try again with another datacenter
        
        if len(data) == 0:
            result = self.client.execute_report(
                        report_id         = report_id, 
                        parameters        = parameters,
                        datacenter        = "dca1" if datacenter == "phx2" else "phx2",
                        timeout           = timeout,
                        pii               = True,
                        cancel_if_timeout = True
            )
            data = result.to_pandas(with_headers = headers)
        """

        # ------------------------------------- 2. Load Metadata -------------------------------------- #
        # 2. Determine if it succeeded (completed_success or finished_success in metadata status)

        metadata = result.metadata
        if not metadata["error_metadata"]:
            num_rows = data.shape[0]  # metadata["row_count"]
            queue_sec = metadata["queue_time_seconds"]
            exec_sec = metadata["execution_time_seconds"]

            self.mk1.logging.logger.info(
                f"(QueryAltantisAPI.run_query) [Success] Rows: {num_rows} / Queue: {queue_sec} / Execution: {exec_sec}s"
            )
            return data, metadata

        else:
            e = (
                metadata["error_message"]
                if metadata["error_message"] != ""
                else "Error not available."
            )
            self.mk1.logging.logger.error(
                f"(QueryAltantisAPI.run_query) [Failed]  Query could not run! Error message: {e}"
            )
            raise QueryRunnerException(e)
            
            
            
            
            
            
            
            
            
            
            