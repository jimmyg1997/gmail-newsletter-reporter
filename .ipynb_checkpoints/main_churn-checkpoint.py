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
            "--operation", 
            type    = str,  
            default = "close_cases" , 
            help    = "Options = {create_cases, close_cases, prepare_cases}"
        ) 
        return parser.parse_args()
    
    ## *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-* UPDATE LOGS *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##
      
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
        
        
        ## *-*-* 1. Data Loader > Load data *-*-* ##
        logs  =  data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_current_logs)
        logs.columns = list(kirby_casting_map_restos.keys())
        
        
        ## *-*-* 2. Salesforce > Cases Preparation  *-*-* ##
        for idx, row in tqdm(logs.iterrows()):
            status     = row["status"]
            level_4__c = row["level_4__c"]
            level_5__c = row["level_5__c"]
            case_id    = row["id"]
            
            sobject_info = salesforce_api.get_sobject_data(
                sobject    = "Case", 
                sobject_id = row["id"]
            )
            
            status     = sobject_info["Status"]
            level_4__c = sobject_info["Level_4__c"]
            level_5__c = sobject_info["Level_5__c"]
            
            logs.loc[idx, "last_modification_date"]= today.strftime("%Y-%m-%d %H:%M:%S")
            logs.loc[idx, "level_4__c"]            = level_4__c
            logs.loc[idx, "level_5__c"]            = level_5__c
            
            print(f"Yes | {case_id} || {row['status']} || {status} || {level_4__c} || {level_5__c}")
            
            if level_4__c == "Admin" and level_5__c == "Closed Overflow" :
                logs.loc[idx,"status"] = "Closed: No Outreach"
                
            
            
            if status == "New" and (level_4__c == "" or level_4__c is None) and (level_5__c == "" or level_5__c is None) :
                
        
                sobject_fields = {
                    "Status"     : "Closed: No Outreach",
                    "Level_4__c" : "Admin",
                    "Level_5__c" : "Closed Overflow"
                }

                salesforce_api.update_sobject(
                        sobject        = "Case",
                        sobject_id     = case_id,
                        sobject_fields = sobject_fields
                )

                sobject_info = salesforce_api.get_sobject_data(
                    sobject    = "Case", 
                    sobject_id = case_id
                )
                logs.loc[idx, "last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
                logs.loc[idx, "status"]                 = sobject_info["Status"] 
                logs.loc[idx, "level_4__c"]             = sobject_info["Level_4__c"]
                logs.loc[idx, "level_5__c"]             = sobject_info["Level_5__c"]
            
        ## *-*-* 4. Data Loader > Write ALL logs to Kirby table *-*-* ##
        
        """
            4.1 Save logs locally
            4.2 Write Logs to kirby table :  
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
        
        # data_loader.write_data_to_google_sheets(
        #     logs, 
        #     cc_id, 
        #     cc_tab_previous_logs, 
        #     spreadsheet_has_headers = True
        # )
        
        

        
        
        
        
        
        
        
                
    ## *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-  [2] CASES CLOSING *-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*- ##
     
        
    def run_cases_closing_v2(self, start_date : str, end_date :str):
        ## *-*-* Configuration (attributes) *-*-* #
        cc_id            = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_countries = str(mk1.config.get("google_sheets","cc_tab_countries"))
        

        ## *-*-* Configuration (objects) *-*-* ##
        google_sheets_api  = GoogleSheetsAPI(self.mk1)
        data_loader        = DataLoader(self.mk1, google_sheets_api)
        salesforce_api     = SalesforceAPI(self.mk1)
        
        
        ## *-*-* 1. Data Loader > Load data *-*-* ##
        """
            1.1 Load `countries_scheduler` from `Control Center` > c:Countries
        """
        countries_scheduler = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_countries)
        owner_ids           = tuple(countries_scheduler["Owner ID"].values)
    
        cases = salesforce_api.query(
            soql_str = "SELECT Id,OwnerId,Status FROM Case "
                       f"WHERE OwnerId IN {owner_ids} "
                       f"AND CreatedDate >= {start_date}T00:00:00Z "
                       f"AND CreatedDate < {end_date}T23:59:59Z "
                       "AND Status = 'New' "
        )
    


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
            seconds         = 10

        )
        
        display(sf_df_report)
        
        
        

        
        
        
    def run_cases_closing_v3(self):
        
         
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
            1.2 Update all cases Status
            1.3 Retrieve all the restaurants that should be checked status ~ {"New", "In Progress", "Opened: In Progress"}
            
        """
  
        logs                 = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_current_logs)
        case_ids             = tuple(logs["id"].values)
        cases                = salesforce_api.query(f"SELECT Id,OwnerId,Status FROM Case WHERE Id IN {case_ids}")
        logs["status"]       = cases["Status"]
        logs["check_status"] = logs.apply(lambda x : x["status"] in ["New", "In Progress", "Opened: In Progress"], axis = 1)
        


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
            
            
        # --------------------------------------------------------------------------------------------------- #
        
        ## *-*-* 3. DataFrame Operations > Check1 , Check2 *-*-* ##
        """
            3.1 Check if restaurant is already onboarded
            3.2 Check if restaurant has already taken trip 
        """
        
        def check_onboarding(row):
            restaurant_uuid   = row["restaurant_uuid__c"]
            check1 = if restaurant_uuid not in list(onboarding_status["uuid"].values)
            check2 = if onboarding_status.loc[ onboarding_status["uuid"] == restaurant_uuid, "Latest_Status"].values == "activated"
            return True if check1 or check2 else False
        
        
        def check_trips(row):
            restaurant_uuid   = row["restaurant_uuid__c"]
            return True if not orders.empty and restaurant_uuid in list(orders["restaurant_uuid"].values) else False
        
        
        def check_final(row):
            
            if not row["check_onboarding"]  :  # if not activated
                return  "Not Activated on Wok"
        
            elif row["check_onboarding"] and row["check_trips"]  : # if activated AND taking trips
                return "Taking Trips"
                
            else : 
                return ""
        
        logs["check_onboarding"]       = logs.apply(lambda x : check_onboarding(x), axis = 1)
        logs["check_trips"]            = logs.apply(lambda x : check_trips(x), axis = 1)
        logs["check_onboarding_trips"] = logs.apply(lambda x : check_final(x), axis = 1)
        
        # --------------------------------------------------------------------------------------------------- #
        
        ## *-*-* 4. Salesforce > Closing Cases *-*-* ##
        sf_df               = pd.DataFrame()
        sf_df["Id"]         = logs["Id"]
        sf_df["Status"]     = logs["Status"]
        sf_df["Status"]     = "Closed: No Outreach"
        sf_df["Level_4__c"] = "Out Of Scope"
        sf_df["Level_5__c"] = logs["check_onboarding_trips"]
        sf_df               = sf_df.loc[sf_df["check_onboarding_trips"] != ""]
        
    
        sf_df_report = salesforce_api.bulk_operation(
            sobject_data_df = sf_df,
            sobject         = "Case",
            sobject_id_type = "Id",
            operation       = "update",
            seconds         = 10

        )
        
        display(sf_df_report)

        
        
 
        
        
        
        
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
        
        
        
        
        # ------------------------------------------------------------------------------------------------------------------------ #
        
        ## *-*-* 1. Data Loader > Load data *-*-* ##
        """
            1.1 Load `logs` from `Control Center` > CurrentCaseLogs
        """
        logs  = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_current_logs)

        
        ## *-*-* 2. Salesforce > Retrieve Status Information  *-*-* ##
        """
            Per merchant : 
                2.1 Retrieve the information from Salesforce. Check the "Status"
                2.2 Update "Status" at `logs`
                2.3 Check if status in (New, In Progress) and add to `restos_checking`
            
        """
        
        restos_checking = []
        
        for idx, row in tqdm(logs.iterrows(), total = len(logs)):
            
            
            sobject_info = salesforce_api.get_sobject_data(
                sobject    = "Case", 
                sobject_id = row["id"]
            )
            status = sobject_info["Status"]
            logs.loc[idx, "last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
            logs.loc[idx, "status"]                 = status
            
            #print(f"Id : {row['id']} | Status : {status}")

            if status in ["New", "In Progress", "Opened: In Progress"] : 
                restos_checking.append(row["restaurant_uuid__c"])
                
        display(logs)
        print(logs["status"].unique())
        print(f"Restos to be checked : {len(restos_checking)}")
        
        
        
                
        ## *-*-* 3. Queryrunner > Retrieve info for the restaurants oto be checked  *-*-* ##
        """
            3.1 Retrieve Onboarding status for `restos_checking`
            3.2 Retrieve Live orders for `restos_checking` by chunking them 
                - Chunk the `restos_checking` into chunks of size 200 
                - Execute and retrieve the live orders for the chunk into `orders_chunk`
                - Append `orders_chunk` into the final orders dataframe `orders`
        """
        onboarding_status = data_loader.load_data_from_query_atlantis(
            report_id = report_id_resto_onboarding, 
            params    = {"restaurant_uuids" : "'" + "','".join(restos_checking) + "'"}
        )
        
        
        restos_checking_chunked = chunkify(restos_checking, 50)
        orders = pd.DataFrame()
        
        
        for chunk in  tqdm(restos_checking_chunked, total = len(restos_checking_chunked)) : 
            orders_chunk = data_loader.load_data_from_query_neutrino(
                report_id = report_id_restos_live, 
                params    = {"restaurant_uuids" : "'" + "','".join(chunk) + "'"}
            )
            orders = orders.append(orders_chunk)
            
        print(restos_checking) 
        display(orders)
            
        
        ## *-*-* 4. Salesforce > Autoclose cases  *-*-* ##
        """
            Per merchant :
                - If resto "Inactive" :
                    4.1.1 Autoclose by using the method `update_sobject()` if a resto got inactive 
                    4.1.2 Update the logs properly
                    
                - If resto "Active"
                    4.2.1 Autoclose by using the method `update_sobject()` if took trip the last 7 days (so no need top be in the queue)
                    4.2.2 Retrieve the data of the case again with the method `get_sobject_data()` for valiation purposes
                    4.2.3 Update the logs properly
        """
        


        for idx, row in tqdm(logs.iterrows(), total = len(logs)):
    
            if row["restaurant_uuid__c"] not in restos_checking : continue
            
         
            ## *-*-* Configuration (attributes) *-*-* ##
            case_id           = row["id"]
            restaurant_uuid   = row["restaurant_uuid__c"]
            
            if restaurant_uuid not in list(onboarding_status["uuid"].values) : 
                flag_is_activated = True
            else : 
                if onboarding_status.loc[ onboarding_status["uuid"] == restaurant_uuid, "Latest_Status"].values == "activated" : 
                    flag_is_activated = True
                else : 
                    
                    flag_is_activated = False
                    
            flag_had_trip = True if not orders.empty and restaurant_uuid in list(orders["restaurant_uuid"].values) else False
            
            sobject_fields = {
                "Status"     : "Closed: Resolved",
                "Level_4__c" : "Out Of Scope",
                "Level_5__c" : ""
            }
            
            
            ## *-*-* Autoclosing cases *-*-* ##
            
            if not flag_is_activated  : 
                sobject_fields["Level_5__c"] = "Not Activated on Wok"
                
            elif flag_is_activated and flag_had_trip  :
                sobject_fields["Level_5__c"] = "Taking Trips"
                
            else : continue
            
            
            
            print(f"{idx_checking} out of {len(restos_checking)} : WOK {flag_is_activated} / TRIP {flag_had_trip}")
                
            salesforce_api.update_sobject(
                    sobject        = "Case",
                    sobject_id     = case_id,
                    sobject_fields = sobject_fields
            )
            time.sleep(1)
            
            # Retrieve the data again for valiation purposes
            sobject_info = salesforce_api.get_sobject_data(
                sobject    = "Case", 
                sobject_id = case_id
            )
            logs.loc[idx, "last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
            logs.loc[idx, "status"]                 = sobject_info["Status"] 
            logs.loc[idx, "level_4__c"]             = sobject_info["Level_4__c"]
            logs.loc[idx, "level_5__c"]             = sobject_info["Level_5__c"]
            
            
            ## *-*-* Write logs (locally,`Control Center` > CurrentLogs)   *-*-* ##
            logs.to_csv(
                path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
                index       = False
            )
 
    
        ## *-*-* 5. Data Loader > Write logs  *-*-* ##
        """
            5.1 Save logs locally
            5.2 Write Logs to kirby table 
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
        restos_expanded = restos_expanded[restos_expanded["Owner ID"] == "00G1J000003PKHiUAO"]
        print(f"[No. of Restaurants] [After filtering] = {len(restos_expanded)}")
        
        restos_expanded = restos_expanded.reset_index()
        display(restos_expanded)
        


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
        sf_df["Restaurant_UUID__c"] = restos_expanded["restaurant_uuid"]
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

        ## --------- Logs
        logs                           = pd.DataFrame(columns = list(kirby_casting_map_restos.keys()), index = range(len(restos_expanded)))
        logs["creation_date"]          = today.strftime("%Y-%m-%d %H:%M:%S") 
        logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
        logs["status"]                 = "New"
        logs["id"]                     = sf_df_report["sf__Id"]
        logs["salesforce_view_link"]   = logs.apply(lambda x : salesforce_api.get_request_urls()["production"].format(sobject = "Case",sobject_id = x["id"]), axis = 1)
        logs["subject"]                = sf_df_report["Subject"]
        logs["onwer_id"]               = sf_df_report["OwnerId"]
        logs["account_id"]             = sf_df_report["AccountId"]
        logs["restaurant_uuid__c"]     = sf_df_report["Restaurant_UUID__c"]
        logs["origin"]                 = sf_df_report["Origin"]
        logs["type"]                   = sf_df_report["Type"]
        logs["record_type_id"]         = sf_df_report["RecordTypeId"]
        logs["kpi__c"]                 = sf_df_report["KPI__c"]
        logs["project_type__c"]        = sf_df_report["Project_Type__c"]
        logs["level_2__c"]             = sf_df_report["Level_2__c"]
        logs["level_3__c"]             = sf_df_report["Level_3__c"]
        logs["level_4__c"]             = sf_df_report["Level_4__c"]
        logs["level_5__c"]             = sf_df_report["Level_5__c"]
        logs["country_name"]           = restos_expanded["country_name"]
        logs["restaurant_segment"]     = restos_expanded["restaurant_segment"]
        logs["restaurant_category"]    = restos_expanded["restaurant_category"]
        logs["restaurant_direct"]      = restos_expanded["restaurant_direct"]
        logs["restaurant_name"]        = restos_expanded["restaurant_name"].apply(lambda x: x.decode('utf-8'))
        logs["error_status"]           = sf_df_report["status"]
        logs                           = logs[logs["error_status"] != "Failed"]
        del logs["error_status"]
        display(logs)
        
                
        ## *-*-* 5. Data Loader > Write ALL logs  *-*-* ##
        """
            5.1 Save logs locally
            5.2 Write Logs to kirby table
            5.3 Write logs to Control Cente > CurrentCase
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
        
        
        
        
        
        
        
        
        

#     def run_cases_creation_v2(self) :
#         ## *-*-* Configuration (attributes) *-*-* #
#         today                    = (dt.datetime.now() - dt.timedelta(days = 0))
#         cc_id                    = str(mk1.config.get("google_sheets","cc_id"))
#         cc_tab_countries         = str(mk1.config.get("google_sheets","cc_tab_countries"))
#         cc_tab_resto_exclusions  = str(mk1.config.get("google_sheets","cc_tab_resto_exclusions"))
#         cc_tab_current_logs      = str(mk1.config.get("google_sheets","cc_tab_current_logs"))
#         report_id_restos         = str(mk1.config.get("queryrunner","churn_restaurants_report_id"))
#         fn_path_restos           = str(mk1.config.get("app_storage","chrun_restaurants"))
#         fn_path_restos_logs      = str(mk1.config.get("app_storage","chrun_restaurants_logs"))
#         kirby_tb_restos          = str(mk1.config.get("kirby", "churn_restaurants_table_name"))
#         kirby_casting_map_restos = churn_restaurants_casting_map # from utils
         
    
#         ## *-*-* Configuration (objects) *-*-* ##
#         google_sheets_api  = GoogleSheetsAPI(self.mk1)
#         query_atlantis_api = QueryAtlantisAPI(self.mk1)
#         kirby_api          = KirbyAPI(self.mk1)
#         data_loader        = DataLoader(self.mk1, google_sheets_api, query_atlantis_api,None, kirby_api)
#         salesforce_api     = SalesforceAPI(self.mk1)
        
#         # ------------------------------------------------------------------------------------------------------------------------ #
        
#         ## *-*-* 1. Data Loader > Load `restos` data from queryrunner atlantis *-*-* ##
#         """
#             1.1 Load the dataframe
#             1.2 Keep only those that do not have empty values in (`restaurant_segment`, `restaurant_category`, `restaurant_direct`, `accountId`)
            
#         """

#         if not os.path.exists(fn_path_restos.format(today.strftime("%Y_%m_%d"))) :
#             restos = data_loader.load_data_from_query_atlantis(
#                 report_id  = report_id_restos, 
#                 params = {
#                     "RoR_Countries" : "''",
#                     "Churn_RoR"     : 0.05
#                 }
#             )
#             restos.to_csv(fn_path_restos.format(today.strftime("%Y_%m_%d")), index = False)
            
#         else :
#             restos = pd.read_csv(fn_path_restos.format(today.strftime("%Y_%m_%d")), index_col  = 0)
#             restos = restos.reset_index()
            
            
#         restos = restos[restos["AccountId"]           != "\\N"]
#         restos = restos[restos["restaurant_segment"]  != "\\N"]
#         restos = restos[restos["restaurant_category"] != "\\N"]
#         restos = restos[restos["restaurant_direct"]   != "\\N"]
            
        
#         ## *-*-* 2. Data Loader > Loading `countries_scheduler` *-*-* ##
#         """
#             2.1 Loading `countries_scheduler` from `Control Center` > c:Countries
#             2.2 Loading `restos_to_be_excluded`     from `Control Center` > c:RestosExclusion
#         """
#         countries_scheduler   = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_countries)
#         countries_scheduler   = countries_scheduler.rename({"Country" : "country_name"}, axis = 1)
#         restos_to_be_excluded = data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_resto_exclusions)
        


#         ## *-*-* 3. DataFrame opertations > Combine `countries_scheduler` and `restos`  *-*-* ##
#         """
#             3.1 Merge `countries_scheduler` and `restos` 
#             3.2 Filtering based on the filter given for Restaurant (Segment, Category, Direct) 
#         """
#         def filtering(row) : 
#             check_segment  = row[row["restaurant_segment"]]  == "TRUE"
#             check_category = row[row["restaurant_category"]] == "TRUE"
#             check_direct   = row[row["restaurant_direct"]]   == "TRUE"
#             check_uuid     = row["restaurant_uuid"] not in list(restos_to_be_excluded[row["country_name"]].values)

#             return True if (check_segment and check_category and check_direct and check_uuid) else False
        

#         print(f"[No. of Restaurants] [Initially] = {len(restos)}")
#         restos_expanded                    = restos.merge(countries_scheduler, on = 'country_name')
#         restos_expanded["Keep Restaurant"] = restos_expanded.apply(lambda x : filtering(x), axis = 1)
#         restos_expanded                    = restos_expanded[restos_expanded["Keep Restaurant"] == True]
#         print(f"[No. of Restaurants] [After filtering] = {len(restos_expanded)}")
        


#         ## *-*-* 4. Salesforce > Create cases per region *-*-* ##
#         """
#             Per merchant : 
#                 4.1 Configuration for the sobject_fields
#                 4.2 Insert new Case in the respective Salesforce queue
#                 4.3 Get the respective salesforce link for the Case
#                 4.4 Append the logs in the dataframe `logs`
            
#         """
#         logs = pd.DataFrame(columns = list(kirby_casting_map_restos.keys()))
#         data_loader.clear_google_sheets_tab(cc_id, cc_tab_current_logs)
        
#         for idx, row in tqdm(restos_expanded.iterrows(), total = len(restos_expanded)):
            
#             #print(f"----------> Pushing to : [AUTOMATION] {row['country_name']};{row['restaurant_name']}")
#             sobject_fields = {
#                     "Status"              : "New",
#                     "Origin"              : "Pro-Active Support",
#                     "Type"                : "Restaurants",
#                     "AccountId"           : row["AccountId"],
#                     "RecordTypeId"        : "0121J0000016fNFQAY",
#                     "OwnerId"             : row["Owner ID"],
#                     "Restaurant_UUID__c"  : row["restaurant_uuid"],
#                     "Subject"             : f"[AUTOMATION] {row['country_name']};{row['restaurant_name']}",
#                     "KPI__c"              : "Soft Churn",
#                     "Project_Type__c"     : "Outbound Retention",
#                     "Level_2__c"          : "Other",
#                     "Level_3__c"          : "Churn Re-engagement",
#                     "Level_4__c"          : "",
#                     "Level_5__c"          : "",
                    
#                 }
#             print(sobject_fields)
#             #time.sleep(2)
#             try : 
            
#                 sobject_id = salesforce_api.insert_sobject(
#                     sobject        = "Case",
#                     sobject_fields = sobject_fields
#                 )

                
#                 salesforce_link = salesforce_api.get_request_urls()["production"].format(
#                     sobject    = "Case",
#                     sobject_id = sobject_id
#                 )

#                 logs = logs.append(pd.Series([
#                             today.strftime("%Y-%m-%d %H:%M:%S"),
#                             today.strftime("%Y-%m-%d %H:%M:%S"),
#                             sobject_fields["Status"],
#                             salesforce_link,
#                             sobject_fields["Subject"],
#                             sobject_id,
#                             sobject_fields["OwnerId"],
#                             sobject_fields["AccountId"],
#                             sobject_fields["Restaurant_UUID__c"],
#                             sobject_fields["Origin"],
#                             sobject_fields["Type"],
#                             sobject_fields["RecordTypeId"],
#                             sobject_fields["KPI__c"],
#                             sobject_fields["Project_Type__c"],
#                             sobject_fields["Level_2__c"],
#                             sobject_fields["Level_3__c"],
#                             sobject_fields["Level_4__c"],
#                             sobject_fields["Level_5__c"],
#                             row["country_name"],
#                             row["restaurant_segment"],
#                             row["restaurant_category"],
#                             row["restaurant_direct"],
#                             row["restaurant_name"]

#                 ], index = logs.columns) , ignore_index = True)
                
#                 print(f"------------------> SUCCESS")

                
#             except : 
#                 print(f"------------------> FAILED")
#                 continue
                
            

                
#         ## *-*-* 5. Data Loader > Write ALL logs to Kirby table *-*-* ##
#         """
#             5.1 Save logs locally
#             5.2 Write Logs to kirby table : 
#         """
#         logs.to_csv(
#             path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
#             index       = False
#         )
#         data_loader.write_data_to_kirby(
#             df          = logs, 
#             table_name  = kirby_tb_restos, 
#             casting_map = kirby_casting_map_restos, 
#             file_path   = fn_path_restos_logs.format(today.strftime("%Y_%m_%d"))
#         )


         
        
        
    def run(self):
        operation = self.args.operation
        
        self.run_cases_closing_v2(start_date = "2023-04-10", end_date = "2023-04-21")
        
#         if operation == "create_cases" : 
#             self.run_cases_creation()
            
#         elif operation == "close_cases" : 
#             self.run_cases_closing()
            
#         elif operation == "prepare_cases" : 
#             self.run_cases_preparation()
        
        #self.run_update_logs(operation)

    
        

if __name__ == '__main__':

    mk1        = MkI.get_instance(_logging = True)
    controller = Controller(mk1)
    controller.run()

