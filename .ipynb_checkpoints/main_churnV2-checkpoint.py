#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    [*] Description : Churn Program Retention
    [*] Author      : dimitrios.georgiou@uber.com 
    [*] Date        : Feb 10, 2023
    [*] Links       :  
"""

# -*-*-*-*-*-*-*-*-*-*-* #
#     Basic Modules      #
# -*-*-*-*-*-*-*-*-*-*-* #
import os
import json
import argparse
import time
import numpy     as np
import functools as ft
import pandas    as pd
import datetime  as dt
from tqdm            import tqdm
from typing          import Dict, Any, List
from IPython.display import display



# -*-*-*-*-*-*-*-*-*-*-* #
#     Project Modules    #
# -*-*-*-*-*-*-*-*-*-*-* #

from lib.framework.markI         import *
from lib.handlers.data_handler   import DataLoader
from lib.modules.API_google      import GoogleSheetsAPI
from lib.modules.API_queryrunner import QueryAtlantisAPI, QueryNeutrinoAPI
from lib.modules.API_kirby       import KirbyAPI
from lib.modules.API_salesforce  import SalesforceAPI
from lib.helpers.utils           import *


class Controller():
    def __init__(self, mk1 : MkI) : 
        ## Mark1
        self.mk1  = mk1
        self.args = self.parsing()

    
    def parsing(self): 
        parser = argparse.ArgumentParser()
        ## *-*-* MAIN *-*-* ##
        parser.add_argument(
            "-o",
            "--operation", 
            type    = str,  
            default = "close_cases" , 
            help    = "Options = {create_cases, close_cases, prepare_cases}"
        ) 
        
        parser.add_argument(
            "-bs",
            "--backfill_start_date", 
            type    = str,  
            default = "2023-05-08" , 
            help    = "The starting date for the backfilling process"
        ) 
        
        parser.add_argument(
            "-be",
            "--backfill_end_date", 
            type    = str,  
            default = "2023-05-09" , 
            help    = "The starting date for the backfilling process"
        ) 
        
        parser.add_argument(
            "-bst",
            "--backfill_statuses", 
            type    = str,  
            default = "" , 
            help    = "The statuses to be checked for the backfilling process"
        ) 
        return parser.parse_args()
    
    ## *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* UPDATE LOGS *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##
      
    """
    def run_update_logs(self, operation = "prepare_cases"):
        ## *-*-* Configuration (attributes) *-*-* #
        today                      = (dt.datetime.now() - dt.timedelta(days = 0))
        cc_id                      = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_current_logs        = str(mk1.config.get("google_sheets","cc_tab_current_logs"))
        cc_tab_previous_logs       = str(mk1.config.get("google_sheets","cc_tab_previous_logs"))
        fn_path_restos_logs        = str(mk1.config.get("app_storage","chrun_restaurants_logs"))
        
        ## *-*-* Configuration (objects) *-*-* ##
        google_sheets_api  = GoogleSheetsAPI(self.mk1)
        data_loader        = DataLoader(self.mk1, google_sheets_api)
        
        ## *-*-* 1. Data Loader > Load data *-*-* ##
        logs = pd.read_csv(
            filepath_or_buffer = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
            index_col          = False
        )
        
        ## *-*-* 2. Data Loader > Write ALL logs to Kirby table *-*-* ##
        data_loader.write_data_to_google_sheets(
            logs, 
            cc_id, 
            cc_tab_previous_logs if operation == "prepare_cases" else cc_tab_current_logs,
            spreadsheet_has_headers = True
        )
    """
    
    
    
    ## *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* [1] CASES PREPARATION *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##
    
    
    def run_cases_preparation(self) : 
        ## *-*-* Configuration (attributes) *-*-* #
        today                      = (dt.datetime.now() - dt.timedelta(days = 0))
        cc_id                      = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_current_logs        = str(mk1.config.get("google_sheets","cc_tab_current_logs"))
        cc_tab_previous_logs       = str(mk1.config.get("google_sheets","cc_tab_previous_logs"))
        fn_path_restos_logs        = str(mk1.config.get("app_storage","chrun_restaurants_logs"))
        kirby_tb_restos            = str(mk1.config.get("kirby", "churn_restaurants_table_name"))
        kirby_casting_map_restos   = churn_restaurants_casting_map # from utils
        
        ## *-*-* Configuration (objects) *-*-* ##
        google_sheets_api  = GoogleSheetsAPI(self.mk1)
        query_atlantis_api = QueryAtlantisAPI(self.mk1)
        query_neutrino_api = QueryNeutrinoAPI(self.mk1)
        kirby_api          = KirbyAPI(self.mk1)
        data_loader        = DataLoader(self.mk1, google_sheets_api, query_atlantis_api, query_neutrino_api, kirby_api)
        salesforce_api     = SalesforceAPI(self.mk1)
        


        ## *-*-* 1. Salesforce > Update Status *-*-* ##
        """
            1.1 Load `logs` from `Control Center` > CurrentCaseLogs
            1.2 Retrieve all the cases from SF in a chunkify way
            1.3 Update all cases Status
            1.4 Retrieve all the restaurants that should be checked status ~ {"New", "In Progress", "Opened: In Progress"}
            
        """
        def read_chunkify(case_ids):
            cases = pd.DataFrame()
            case_ids_chunked = chunkify(case_ids, 50)
            for case_ids_chunk in tqdm(case_ids_chunked, total = len(case_ids_chunked)) : 
                cases_chunk = salesforce_api.query(f"SELECT Id,OwnerId,Status,Level_4__c,Level_5__c "
                                                   f"FROM Case WHERE Id IN {tuple(case_ids_chunk)}")
                cases = cases.append(cases_chunk)
                
            cases = cases.reset_index()
                
            return cases
  
        logs                           = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_current_logs)
        case_ids                       = list(logs["id"].values)
        cases                          = read_chunkify(case_ids)
        logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
        logs["status"]                 = cases["Status"]
        logs["level_4__c"]             = cases["Level_4__c"]
        logs["level_5__c"]             = cases["Level_5__c"]
        
        
        
        ## *-*-* 2. Salesforce > Cases Preparation  *-*-* ##
        sf_df                       = pd.DataFrame()
        sf_df["Id"]                 = logs["id"]
        sf_df["Status"]             = logs["status"]
        sf_df["Restaurant_UUID__c"] = logs["restaurant_uuid__c"]
        sf_df["Level_4__c"]         = logs["level_4__c"]
        sf_df["Level_5__c"]         = logs["level_5__c"]
        sf_df                       = sf_df.loc[ (sf_df["Status"] == "New") \
                                                & ( (sf_df["Level_4__c"] == "") |  (sf_df["Level_4__c"].isnull()) ) \
                                                & ( (sf_df["Level_5__c"] == "") |  (sf_df["Level_5__c"].isnull()) )      ] 

        sf_df["Status"]             = "Closed: No Outreach"
        sf_df["Level_4__c"]         = "Admin"
        sf_df["Level_5__c"]         = "Closed Overflow"
        
        
        print(f"[No. of Restaurants] [Actually SF Updating] = {len(sf_df)}")
        
        sf_df_report = salesforce_api.bulk_operation(
            sobject_data_df = sf_df,
            sobject         = "Case",
            sobject_id_type = "Id",
            operation       = "update",
            seconds         = 10

        )
        
        # --------------------------------------------------------------------------------------------------- #
        
    
        def update_logs(row):
            if row["restaurant_uuid__c"] in list(sf_df_report["Restaurant_UUID__c"].values) : 
                status     = sf_df_report.loc[ sf_df_report["Restaurant_UUID__c"] == row["restaurant_uuid__c"], "Status"].values[0]
                level_4__c = sf_df_report.loc[ sf_df_report["Restaurant_UUID__c"] == row["restaurant_uuid__c"], "Level_4__c"].values[0]
                level_5__c = sf_df_report.loc[ sf_df_report["Restaurant_UUID__c"] == row["restaurant_uuid__c"], "Level_5__c"].values[0]
                
            else : 
                status     = row["status"]
                level_4__c = row["level_4__c"]
                level_5__c = row["level_5__c"]

            return pd.Series([status, level_4__c, level_5__c])

  
        logs[["status", "level_4__c", "level_5__c"]] = logs.apply(lambda x : update_logs(x), axis = 1)
    
        
        # --------------------------------------------------------------------------------------------------- #
        
        ## *-*-* 3. Data Loader > Write ALL logs  *-*-* ##
        """
            5.1 Save logs locally
            5.2 Write Logs to kirby table
            5.3 Write logs to Control Center > PreviousCasesLogs
        """
        logs.to_csv(
            path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
            index       = False
        )
        data_loader.write_data_to_kirby(
            df          = logs, 
            table_name  = kirby_tb_restos, 
            casting_map = kirby_casting_map_restos, 
            file_path   = fn_path_restos_logs.format(today.strftime("%Y_%m_%d"))
        )
        
        
        data_loader.clear_google_sheets_tab(
            cc_id, 
            cc_tab_previous_logs
        )
    
        data_loader.write_data_to_google_sheets(
            logs, 
            cc_id, 
            cc_tab_previous_logs,
            spreadsheet_has_headers = True
        )

        
        
        
        
        
        
        


        
        
        
        
        
        
        
                
    ## *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-  [2] CASES CLOSING *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##
    
    def run_cases_closing_backfill(
            self, 
            start_date : str, 
            end_date   : str,
            statuses   : List[str]
        ):
        ## *-*-* Configuration (attributes) *-*-* #
        cc_id               = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_countries    = str(mk1.config.get("google_sheets","cc_tab_countries"))
        cc_tab_current_logs = str(mk1.config.get("google_sheets","cc_tab_current_logs"))
        

        ## *-*-* Configuration (objects) *-*-* ##
        google_sheets_api  = GoogleSheetsAPI(self.mk1)
        data_loader        = DataLoader(self.mk1, google_sheets_api)
        salesforce_api     = SalesforceAPI(self.mk1)
        
        
        ## *-*-* 1. Data Loader > Load data *-*-* ##
        """
            1.1 Load `countries_scheduler` from `Control Center` > c:Countries
        """
        logs                = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_current_logs)
        countries_scheduler = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_countries)
        owner_ids           = tuple(countries_scheduler["Owner ID"].values)
        statuses            = tuple(statuses) if statuses != [] else ('New', 
                                                                      'Closed: Resolved', 
                                                                      'Closed: Unresolved',
                                                                      #'Closed: No Outreach',
                                                                      'Opened: In Progress',
                                                                      'Opened: Customer Responded',
                                                                      'Pending Customer',
                                                                      'In Progress')
        
        cases = salesforce_api.query(
            soql_str = "SELECT Id,OwnerId,Status FROM Case "
                       f"WHERE OwnerId IN {owner_ids} "
                       f"AND CreatedDate >= {start_date}T00:00:00Z "
                       f"AND CreatedDate < {end_date}T23:59:59Z "
                       f"AND Status IN {statuses} " # f"AND Status IN ('New') "
        )
        display(cases)
        cases = cases[~cases["Id"].isin(logs["id"])]
        #cases = cases[cases["Id"].isin(logs["id"])]
        display(logs)
        display(cases)
        return 

        
        ## *-*-* 2. Salesforce > Closing Cases *-*-* ##
        sf_df               = pd.DataFrame()
        sf_df["Id"]         = cases["Id"]
        sf_df["OwnerId"]    = cases["OwnerId"]
        sf_df["Status"]     = "Closed: No Outreach"
        sf_df["Level_4__c"] = "Out Of Scope"
        sf_df["Level_5__c"] = "Duplicate Case"
        
        display(sf_df)

        sf_df_report = salesforce_api.bulk_operation(
            sobject_data_df = sf_df,
            sobject         = "Case",
            sobject_id_type = "Id",
            operation       = "update",
            seconds         = 5

        )
        

        
        
   
        
        
    def run_cases_closing(self):
         
        ## *-*-* Configuration (attributes) *-*-* #
        today                      = (dt.datetime.now() - dt.timedelta(days = 0))
        cc_id                      = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_queues              = str(mk1.config.get("google_sheets","cc_tab_queues"))
        cc_tab_current_logs        = str(mk1.config.get("google_sheets","cc_tab_current_logs"))
        fn_path_restos_logs        = str(mk1.config.get("app_storage","chrun_restaurants_logs"))
        report_id_resto_onboarding = str(mk1.config.get("queryrunner","churn_restaurants_onboarding_report_id"))
        report_id_restos_live      = str(mk1.config.get("queryrunner","churn_restaurants_live_report_id"))
        kirby_tb_restos            = str(mk1.config.get("kirby", "churn_restaurants_table_name"))
        kirby_casting_map_restos   = churn_restaurants_casting_map # from utils
        
        
        ## *-*-* Configuration (objects) *-*-* ##
        google_sheets_api  = GoogleSheetsAPI(self.mk1)
        query_atlantis_api = QueryAtlantisAPI(self.mk1)
        query_neutrino_api = QueryNeutrinoAPI(self.mk1)
        kirby_api          = KirbyAPI(self.mk1)
        data_loader        = DataLoader(self.mk1, google_sheets_api, query_atlantis_api, query_neutrino_api, kirby_api)
        salesforce_api     = SalesforceAPI(self.mk1)
        
        
        ## *-*-* 1. Salesforce > Update Status *-*-* ##
        """
            1.1 Load `logs` from `Control Center` > CurrentCaseLogs
            1.2 Retrieve all the cases from SF in a chunkify way
            1.3 Update all cases Status
            1.4 Retrieve all the restaurants that should be checked status ~ {"New", "In Progress", "Opened: In Progress"}
            
        """
        
        def read_chunkify(case_ids):
            cases = pd.DataFrame()
            case_ids_chunked = chunkify(case_ids, 50)
            for case_ids_chunk in tqdm(case_ids_chunked, total = len(case_ids_chunked)) : 
                cases_chunk = salesforce_api.query(f"SELECT Id,OwnerId,Status,Level_4__c,Level_5__c "
                                                   f"FROM Case WHERE Id IN {tuple(case_ids_chunk)}")
                cases = cases.append(cases_chunk)
            cases = cases.reset_index()
            return cases
            
  
        logs                           = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_current_logs)
        logs                           = logs.drop_duplicates(subset = ["id"], keep = "first")
        logs                           = logs.dropna(subset = ["status"])
        case_ids                       = list(logs["id"].values)
        cases                          = read_chunkify(case_ids)
        logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
        logs["status"]                 = cases["Status"]
        logs["level_4__c"]             = cases["Level_4__c"]
        logs["level_5__c"]             = cases["Level_5__c"]
        #logs["check_status"]           = logs.apply(lambda x : x["status"] in ["New", "In Progress", "Opened: In Progress"], axis = 1)
        logs["check_status"]           = logs.apply(lambda x : x["level_4__c"] in ["", " ", None] , axis = 1)
        
        
        display(list(cases["Status"].unique()))
        display(logs)
        print(f"[No. of Restaurants] [Initially] = {len(logs)}")


        # --------------------------------------------------------------------------------------------------- #
    
        ## *-*-* 2. Queryrunner > Retrieve info for the restaurants oto be checked  *-*-* ##
        """
            2.1 Retrieve Onboarding status for `restos_checking`
            2.2 Retrieve Live orders for `restos_checking` by chunking them 
                - Chunk the `restos_checking` into chunks of size 50 
                - Execute and retrieve the live orders for the chunk into `orders_chunk`
                - Append `orders_chunk` into the final orders dataframe `orders`
        """
        
        resto_uuids_checking = list(logs.loc[ logs["check_status"] == True, "restaurant_uuid__c"].values)
        print(f"[No. of Restaurants] [To be checked] = {len(resto_uuids_checking)}")
        
        ## 2.1 [Check] Onboarding / Activated on Wok
        onboarding_status = data_loader.load_data_from_query_atlantis(
            report_id = report_id_resto_onboarding, 
            params    = {"restaurant_uuids" : "'" + "','".join(resto_uuids_checking) + "'"}
        )
        
        ## 2.2 [Check] Taking Trips 
        resto_uuids_checking_chunked = chunkify(resto_uuids_checking, 50)
        orders = pd.DataFrame()
        
        for chunk in  tqdm(resto_uuids_checking_chunked, total = len(resto_uuids_checking_chunked)) : 
            orders_chunk = data_loader.load_data_from_query_neutrino(
                report_id = report_id_restos_live, 
                params    = {"restaurant_uuids" : "'" + "','".join(chunk) + "'"}
            )
            orders = orders.append(orders_chunk)
            
            

        print(f"[No. of Restaurants] [To be checked] [Taking Trips] = {len(orders)}")
        print(f"[No. of Restaurants] [To be checked] [Activated on WOK] = {len(onboarding_status)}")
            
            
        # --------------------------------------------------------------------------------------------------- #
        
        ## *-*-* 3. DataFrame Operations > Check1 , Check2 *-*-* ##
        """
            3.1 Check if restaurant is already onboarded
            3.2 Check if restaurant has already taken trip 
        """
        
        def check_onboarding(row):
            restaurant_uuid   = row["restaurant_uuid__c"]
            check1 = True if restaurant_uuid not in list(onboarding_status["uuid"].values) else False
            check2 = True if onboarding_status.loc[ onboarding_status["uuid"] == restaurant_uuid, "Latest_Status"].values == "activated" else False
            return True if check1 or check2 else False
        
        
        def check_trips(row):
            restaurant_uuid   = row["restaurant_uuid__c"]
            return True if not orders.empty and restaurant_uuid in list(orders["restaurant_uuid"].values) else False
        
        
        def check_final(row):
            
            if not row["check_status"] : # if restaurant should not be checked at all
                return ""
            
            elif not row["check_onboarding"]  :  # if not activated
                return  "Not Activated on Wok"
        
            elif row["check_onboarding"] and row["check_trips"]  : # if activated AND taking trips
                return "Taking Trips"
                
            else : # if restaurants should have been checked but it is activated and takes no trips
                return ""
        
        logs["check_onboarding"]       = logs.apply(lambda x : check_onboarding(x), axis = 1)
        logs["check_trips"]            = logs.apply(lambda x : check_trips(x), axis = 1)
        logs["check_onboarding_trips"] = logs.apply(lambda x : check_final(x), axis = 1)
        
        display(logs)
        
        # --------------------------------------------------------------------------------------------------- #
        ## *-*-* 4. Salesforce > Closing Cases *-*-* ##
        sf_df                       = pd.DataFrame()
        sf_df["Id"]                 = logs["id"]
        sf_df["Restaurant_UUID__c"] = logs["restaurant_uuid__c"]
        sf_df["Status"]             = "Closed: Resolved"
        sf_df["Level_4__c"]         = "Out Of Scope"
        sf_df["Level_5__c"]         = logs["check_onboarding_trips"]
        display(sf_df)
        sf_df                       = sf_df.loc[sf_df["Level_5__c"] != ""]
        
        print(f"[No. of Restaurants] [Actually SF Updating] = {len(sf_df)}")
        
        sf_df_report = salesforce_api.bulk_operation(
            sobject_data_df = sf_df,
            sobject         = "Case",
            sobject_id_type = "Id",
            operation       = "update",
            seconds         = 10

        )
        
        # --------------------------------------------------------------------------------------------------- #
        ## *-*-* 5. DataFrame Operations > Update logs *-*-* ##
        
        
        def update_logs(row):
            if row["check_onboarding_trips"] == "" :
                status     = row["status"]
                level_4__c = row["level_4__c"]
                level_5__c = row["level_5__c"]
                
            else :
                status     = sf_df_report.loc[ sf_df_report["Restaurant_UUID__c"] == row["restaurant_uuid__c"], "Status"].values[0]
                level_4__c = sf_df_report.loc[ sf_df_report["Restaurant_UUID__c"] == row["restaurant_uuid__c"], "Level_4__c"].values[0]
                level_5__c = sf_df_report.loc[ sf_df_report["Restaurant_UUID__c"] == row["restaurant_uuid__c"], "Level_5__c"].values[0]
                
            return pd.Series([status, level_4__c, level_5__c])
        
  
        logs[["status", "level_4__c", "level_5__c"]] = logs.apply(lambda x : update_logs(x), axis = 1)
        
        del logs["check_status"]
        del logs["check_onboarding"]
        del logs["check_trips"]
        del logs["check_onboarding_trips"]
        display(logs)
    
            

        
        # --------------------------------------------------------------------------------------------------- #
        
        ## *-*-* 5. Data Loader > Write ALL logs  *-*-* ##
        """
            5.1 Save logs locally
            5.2 Write Logs to kirby table
            5.3 Write logs to Control Center > CurrentCasesLogs
        """
        logs.to_csv(
            path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
            index       = False
        )
        data_loader.write_data_to_kirby(
            df          = logs, 
            table_name  = kirby_tb_restos, 
            casting_map = kirby_casting_map_restos, 
            file_path   = fn_path_restos_logs.format(today.strftime("%Y_%m_%d"))
        )
        data_loader.clear_google_sheets_tab(
            cc_id, 
            cc_tab_current_logs
        )
        
        data_loader.write_data_to_google_sheets(
            logs, 
            cc_id, 
            cc_tab_current_logs,
            spreadsheet_has_headers = True
        )

        
        
        
        
        
    ## *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- [3] CASES CREATION *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##
    def run_cases_creation(self) :
        ## *-*-* Configuration (attributes) *-*-* #
        today                    = (dt.datetime.now() - dt.timedelta(days = 0))
        cc_id                    = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_countries         = str(mk1.config.get("google_sheets","cc_tab_countries"))
        cc_tab_resto_exclusions  = str(mk1.config.get("google_sheets","cc_tab_resto_exclusions"))
        cc_tab_current_logs      = str(mk1.config.get("google_sheets","cc_tab_current_logs"))
        report_id_restos         = str(mk1.config.get("queryrunner","churn_restaurants_report_id"))
        fn_path_restos           = str(mk1.config.get("app_storage","chrun_restaurants"))
        fn_path_restos_logs      = str(mk1.config.get("app_storage","chrun_restaurants_logs"))
        kirby_tb_restos          = str(mk1.config.get("kirby", "churn_restaurants_table_name"))
        kirby_casting_map_restos = churn_restaurants_casting_map # from utils
         
    
        ## *-*-* Configuration (objects) *-*-* ##
        google_sheets_api  = GoogleSheetsAPI(self.mk1)
        query_atlantis_api = QueryAtlantisAPI(self.mk1)
        kirby_api          = KirbyAPI(self.mk1)
        data_loader        = DataLoader(self.mk1, google_sheets_api, query_atlantis_api,None, kirby_api)
        salesforce_api     = SalesforceAPI(self.mk1)
        
        # ------------------------------------------------------------------------------------------------------------------------ #
        
        ## *-*-* 1. Data Loader > Load `restos` data from queryrunner atlantis *-*-* ##
        """
            1.1 Load the dataframe
            1.2 Keep only those that do not have empty values in (`restaurant_segment`, `restaurant_category`, `restaurant_direct`, `accountId`)
            
        """

        if not os.path.exists(fn_path_restos.format(today.strftime("%Y_%m_%d"))) :
            restos = data_loader.load_data_from_query_atlantis(
                report_id  = report_id_restos, 
                params = {
                    "RoR_Countries" : "''",
                    "Churn_RoR"     : 0.05
                }
            )
            restos.to_csv(fn_path_restos.format(today.strftime("%Y_%m_%d")), index = False)
            
        else :
            restos = pd.read_csv(fn_path_restos.format(today.strftime("%Y_%m_%d")), index_col  = 0)
            restos = restos.reset_index()
            
            
        restos = restos[restos["AccountId"]           != "\\N"]
        restos = restos[restos["restaurant_segment"]  != "\\N"]
        restos = restos[restos["restaurant_category"] != "\\N"]
        restos = restos[restos["restaurant_direct"]   != "\\N"]
            
        
        ## *-*-* 2. Data Loader > Loading `countries_scheduler` *-*-* ##
        """
            2.1 Loading `countries_scheduler` from `Control Center` > c:Countries
            2.2 Loading `restos_to_be_excluded`     from `Control Center` > c:RestosExclusion
        """
        countries_scheduler   = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_countries)
        countries_scheduler   = countries_scheduler.rename({"Country" : "country_name"}, axis = 1)
        restos_to_be_excluded = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_resto_exclusions)
        


        ## *-*-* 3. DataFrame opertations > Combine `countries_scheduler` and `restos`  *-*-* ##
        """
            3.1 Merge `countries_scheduler` and `restos` 
            3.2 Filtering based on the filter given for Restaurant (Segment, Category, Direct) 
        """
        def filtering(row) : 
            check_segment  = row[row["restaurant_segment"]]  == "TRUE"
            check_category = row[row["restaurant_category"]] == "TRUE"
            check_direct   = row[row["restaurant_direct"]]   == "TRUE"
            check_uuid     = row["restaurant_uuid"] not in list(restos_to_be_excluded[row["country_name"]].values)

            return True if (check_segment and check_category and check_direct and check_uuid) else False
        
        

        print(f"[No. of Restaurants] [Initially] = {len(restos)}")
        restos_expanded                    = restos.merge(countries_scheduler, on = 'country_name')
        restos_expanded["restaurant_name"] = restos_expanded["restaurant_name"].apply(lambda x: x.encode('utf-8'))
        restos_expanded["Keep Restaurant"] = restos_expanded.apply(lambda x : filtering(x), axis = 1) # for Bulk SF API
        restos_expanded                    = restos_expanded[restos_expanded["Keep Restaurant"] == True]
        #restos_expanded = restos_expanded[restos_expanded["Owner ID"] == "00G1J000003PKHiUAO"]
        restos_expanded = restos_expanded.rename({"restaurant_uuid" : "restaurant_uuid__c"}, axis = 1)
        restos_expanded = restos_expanded.reset_index(drop = True)
        print(f"[No. of Restaurants] [After filtering] = {len(restos_expanded)}")
    
        

        ## *-*-* 4. Salesforce > Create cases per region *-*-* ##
        """

            4.1 Configuration for the sobject_fields
            4.2 Insert new Case in the respective Salesforce queue
            4.3 Get the respective salesforce link for the Case
            4.4 Append the logs in the dataframe `logs`
            4.5 Filter logs to exclude all failed cases
            
        """
        
        ## --------- Salesforce
        sf_df = pd.DataFrame()
        sf_df["AccountId"]          = restos_expanded["AccountId"]
        sf_df["OwnerId"]            = restos_expanded["Owner ID"]
        sf_df["Restaurant_UUID__c"] = restos_expanded["restaurant_uuid__c"]
        sf_df["Subject"]            = restos_expanded.apply(lambda x : f"[AUTOMATION] {x['country_name']};{x['restaurant_name']}", axis = 1)
        sf_df["AccountId"]          = restos_expanded["AccountId"]
        sf_df["Status"]             = "New"
        sf_df["Origin"]             = "Pro-Active Support"
        sf_df["Type"]               = "Restaurants"
        sf_df["RecordTypeId"]       = "0121J0000016fNFQAY"
        sf_df["KPI__c"]             = "Soft Churn"
        sf_df["Project_Type__c"]    = "Outbound Retention"
        sf_df["Level_2__c"]         = "Other"
        sf_df["Level_3__c"]         = "Churn Re-engagement"
        sf_df["Level_4__c"]         = ""
        sf_df["Level_5__c"]         = ""
        


        sf_df_report = salesforce_api.bulk_operation(
            sobject_data_df = sf_df,
            sobject         = "Case",
            sobject_id_type = "Id",
            operation       = "insert",
            seconds         = 5

        )
        
        display(sf_df_report)
        
        
        
        ## --------- Logs
        logs = sf_df_report.copy()
        logs = logs[logs["status"] != "Failed"]
        display(logs)
        logs = logs.rename({
            "sf__Id"             : "id",
            "Subject"            : "subject",
            "OwnerId"            : "onwer_id",
            "AccountId"          : "account_id",
            "Restaurant_UUID__c" : "restaurant_uuid__c",
            "Origin"             : "origin",
            "Type"               : "type",
            "KPI__c"             : "kpi__c",
            "Project_Type__c"    : "project_type__c",
            "RecordTypeId"       : "record_type_id",
            "Level_2__c"         : "level_2__c",
            "Level_3__c"         : "level_3__c",
            "Level_4__c"         : "level_4__c",
            "Level_5__c"         : "level_5__c"
        }, axis = 1)
        
        logs = pd.merge(logs, restos_expanded[[
                            "restaurant_uuid__c",
                            "country_name", 
                            "restaurant_segment", 
                            "restaurant_category", 
                            "restaurant_direct", 
                            "restaurant_name"]] , 
                         on  = "restaurant_uuid__c", 
                         how = "inner")
        logs["restaurant_name"]        = logs["restaurant_name"].apply(lambda x: x.decode('utf-8'))
        logs["creation_date"]          = today.strftime("%Y-%m-%d %H:%M:%S") 
        logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
        logs["status"]                 = "New"
        logs["salesforce_view_link"]   = logs.apply(lambda x : 
                                                    salesforce_api.get_request_urls()["production"].format(
                                                        sobject    = "Case",
                                                        sobject_id = x["id"]), 
                                                    axis = 1)
    
        logs = logs[[
            "creation_date",
            "last_modification_date",
            "status",
            "id",
            "salesforce_view_link",
            "subject",
            "onwer_id",
            "account_id",
            "restaurant_uuid__c",
            "origin",
            "type",
            "record_type_id",
            "kpi__c",
            "project_type__c",
            "level_2__c",
            "level_3__c",
            "level_4__c",
            "level_5__c",
            "country_name",
            "restaurant_segment",
            "restaurant_category",
            "restaurant_direct",
            "restaurant_name"

        ]]

        display(logs)

        ## *-*-* 5. Data Loader > Write ALL logs  *-*-* ##
        """
            5.1 Save logs locally
            5.2 Write Logs to kirby table
            5.3 Write logs to Control Center > CurrentCaseLogs
        """
        logs.to_csv(
            path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
            index       = False
        )
        data_loader.write_data_to_kirby(
            df          = logs, 
            table_name  = kirby_tb_restos, 
            casting_map = kirby_casting_map_restos, 
            file_path   = fn_path_restos_logs.format(today.strftime("%Y_%m_%d"))
        )

        
        data_loader.write_data_to_google_sheets(
            logs, 
            cc_id, 
            cc_tab_current_logs,
            spreadsheet_has_headers = True
        )

    
    def run_cases_update(self) : 
        ## *-*-* Configuration (attributes) *-*-* #
        today                      = (dt.datetime.now() - dt.timedelta(days = 0))
        cc_id                      = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_logs                = str(mk1.config.get("google_sheets","cc_tab_logs"))
        fn_path_restos_logs        = str(mk1.config.get("app_storage","chrun_restaurants_logs"))
        
        ## *-*-* Configuration (objects) *-*-* ##
        google_sheets_api  = GoogleSheetsAPI(self.mk1)
        data_loader        = DataLoader(self.mk1, google_sheets_api)
        salesforce_api     = SalesforceAPI(self.mk1)

        ## *-*-* 1. Salesforce > Update elements *-*-* ##
        
        def read_chunkify(case_ids):
            cases = pd.DataFrame()
            case_ids_chunked = chunkify(case_ids, 50)
            for case_ids_chunk in tqdm(case_ids_chunked, total = len(case_ids_chunked)) : 
                cases_chunk = salesforce_api.query(f"SELECT Restaurant_UUID__c,Id,OwnerId,Status,Level_4__c,Level_5__c "
                                                   f"FROM Case WHERE Id IN {tuple(case_ids_chunk)}")
                cases = cases.append(cases_chunk)
            cases = cases.reset_index()
            return cases
        
        def preprocess_logs(logs) : 
            logs["week_idx"] = logs["week_idx"].astype(int)
            logs             = logs.drop_duplicates(subset = ["id"], keep = "first")
            logs             = logs.dropna(subset = ["status"])
            return logs
    
         
        def update_logs(logs, cases):
            logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
            for idx, row in tqdm(cases.iterrows(), total = len(cases)):
                logs.loc[logs['id'] == row['Id'], 'status']     = row['Status']
                logs.loc[logs['id'] == row['Id'], 'level_4__c'] = row['Level_4__c']
                logs.loc[logs['id'] == row['Id'], 'level_5__c'] = row['Level_5__c']
            return logs
        
  
        all_logs = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_logs)
        all_logs = preprocess_logs(all_logs)
        cases    = read_chunkify(case_ids = list(all_logs["id"].values))
        all_logs = update_logs(all_logs, cases)
        
        
        ## *-*-* 2. Data Loader > Write ALL logs  *-*-* ##
        """
            2.1 Save logs locally
            2.2 Write logs to Control Center > CurrentCasesLogs
        """
        all_logs.to_csv(
            path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
            index       = False
        )
        data_loader.clear_google_sheets_tab(
            cc_id, 
            cc_tab_logs
        )
        data_loader.write_data_to_google_sheets(
            all_logs, 
            cc_id, 
            cc_tab_logs,
            spreadsheet_has_headers = True
        )

    # -------------------------------------------------------------------------------------------------------------------------------------------- 
    # -------------------------------------------------------------------------------------------------------------------------------------------- 
    # -------------------------------------------------------------------------------------------------------------------------------------------- 
        
    def run(self):
        operation = self.args.operation

        if operation == "create_cases" : 
            self.run_cases_creation()

        elif operation == "close_cases" : 
            self.run_cases_closing()

        elif operation == "close_cases_backfill" : 
            start_date = self.args.backfill_start_date
            end_date   = self.args.backfill_end_date
            statuses   = self.args.backfill_statuses.split(",") if self.args.backfill_statuses != '' else []
            self.run_cases_closing_backfill(start_date, end_date, statuses)

        elif operation == "close_cases_duplicates":
            self.run_cases_closing_duplicates_removal()

        elif operation == "prepare_cases" : 
            self.run_cases_preparation()

        elif operation == "update_cases" : 
            self.run_cases_update()

            
   

if __name__ == '__main__':

    mk1        = MkI.get_instance(_logging = True)
    controller = Controller(mk1)
    controller.run()