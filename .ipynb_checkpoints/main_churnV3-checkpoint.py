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
import os, json, time, glob,argparse
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
        parser.add_argument(
            "--days_diff", 
            "-d",
            type    = int,  
            default = 0 , 
            help    = "Days difference from today"
        ) 
        return parser.parse_args()

    
    def run_initialization(self):
        self.google_sheets_api   = GoogleSheetsAPI(self.mk1)
        self.query_atlantis_api  = QueryAtlantisAPI(self.mk1)
        self.query_neutrino_api  = QueryNeutrinoAPI(self.mk1)
        self.kirby_api           = KirbyAPI(self.mk1)
        self.data_loader         = DataLoader(self.mk1, self.google_sheets_api, self.query_atlantis_api, self.query_neutrino_api, self.kirby_api)
        self.salesforce_api      = SalesforceAPI(self.mk1)
        

    def run_update_logs_from_salesforce_and_file(self):
        today = (dt.datetime.now() - dt.timedelta(days = self.args.days_diff))
        
        ## *-*-*-*-*-*-*-*-* Configuration (attributes) *-*-*-*-*-*-*-*-* #
        cc_id               = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_logs         = str(mk1.config.get("google_sheets","cc_tab_logs"))
        fn_path_restos_logs = str(mk1.config.get("app_storage","chrun_restaurants_logs")).format(today.strftime("%Y_%m_%d"))
        dir_storage         = str(mk1.config.get("app","storage_dir"))

        ## --------------------------------------------------------------------------------------------------- ##
        """
            1. (Data Loader) Load logs from `Control Center`
                1.1 If `logs` dataframe empty, find most recents logs, load logs from file
            2. (Salesforce API) read `status`, `L4`, `L5`
            3. Updates logs with correct infromation
            4. Save locally the logs
            5. (Data Loader) Push back to Google Sheets
        """
        try : 
            all_logs = self.data_loader.load_data_from_google_sheets_tab(
                cc_id, 
                cc_tab_logs
            )
            
            if all_logs.empty : 
                pattern = os.path.join(dir_storage, "*_restos_logs.csv")
                fn_paths_restos_logs = glob.glob(pattern)
                fn_path_restos_logs = max(fn_paths_restos_logs)
                
                all_logs = pd.read_csv(
                    filepath_or_buffer = fn_path_restos_logs,
                    index_col          = False
                )
            
            def read_chunkify(case_ids):
                cases = pd.DataFrame()
                case_ids_chunked = chunkify(case_ids, 50)
                for case_ids_chunk in tqdm(case_ids_chunked, total = len(case_ids_chunked)) : 
                    cases_chunk = self.salesforce_api.query(
                        f"SELECT Id,OwnerId,Status,Level_4__c,Level_5__c "
                        f"FROM Case WHERE Id IN {tuple(case_ids_chunk)}"
                    )
                    cases = pd.concat([cases, cases_chunk])
                cases = cases.reset_index()
                return cases

            def update_logs(logs, cases):
                logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
                for idx, row in tqdm(cases.iterrows() , total = len(cases)):
                    logs.loc[logs['id'] == row['Id'], 'status']     = row['Status']
                    logs.loc[logs['id'] == row['Id'], 'level_4__c'] = row['Level_4__c']
                    logs.loc[logs['id'] == row['Id'], 'level_5__c'] = row['Level_5__c']
                return logs

            cases = read_chunkify(
                case_ids = list(all_logs["id"].values)
            )
            
            all_logs = update_logs(
                logs  = all_logs, 
                cases = cases
            )
            
            all_logs.to_csv(
                path_or_buf = fn_path_restos_logs,
                index       = False
            )
            self.data_loader.write_data_to_google_sheets(
                all_logs, 
                cc_id, 
                cc_tab_logs,
                spreadsheet_has_headers = True
            )
        except Exception as e :
            print(f"(Controlller.run_update_logs_from_salesforce) Error : {e}")
            raise e
            
            


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


        ## *-*-* 1. Data Loader > Load data *-*-* ##
        """
            1.1 Load `countries_scheduler` from `Control Center` > c:Countries
        """
        logs                = self.data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_current_logs)
        countries_scheduler = self.data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_countries)
        owner_ids           = tuple(countries_scheduler["Owner ID"].values)
        statuses            = tuple(statuses) if statuses != [] else (
            'New', 
            'Closed: Resolved', 
            'Closed: Unresolved',
            #'Closed: No Outreach',
            'Opened: In Progress',
            'Opened: Customer Responded',
            'Pending Customer',
            'In Progress'
        )

        cases = self.salesforce_api.query(
            soql_str = "SELECT Id,OwnerId,Status FROM Case "
                       f"WHERE OwnerId IN {owner_ids} "
                       f"AND CreatedDate >= {start_date}T00:00:00Z "
                       f"AND CreatedDate < {end_date}T23:59:59Z "
                       f"AND Status IN {statuses} " # f"AND Status IN ('New') "
        )
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


        sf_df_report = self.salesforce_api.bulk_operation(
            sobject_data_df = sf_df,
            sobject         = "Case",
            sobject_id_type = "Id",
            operation       = "update",
            seconds         = 5

        )



   



    


    

        
        
    def run_cases_closing_v3(self):

        ## *-*-* Configuration (attributes) *-*-* #
        today                      = (dt.datetime.now() - dt.timedelta(days = self.args.days_diff))
        # Google Sheets
        cc_id                      = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_queues              = str(mk1.config.get("google_sheets","cc_tab_queues"))
        cc_tab_logs                = str(mk1.config.get("google_sheets","cc_tab_logs"))
        fn_path_restos_logs        = str(mk1.config.get("app_storage","chrun_restaurants_logs"))

        # Queryrunner
        report_id_resto_onboarding = str(mk1.config.get("queryrunner","churn_restaurants_onboarding_report_id"))
        report_id_restos_live      = str(mk1.config.get("queryrunner","churn_restaurants_live_report_id"))

        # Kirby
        kirby_tb_restos            = str(mk1.config.get("kirby", "churn_restaurants_table_name"))
        kirby_casting_map_restos   = churn_restaurants_casting_map # from utils

        ## *-*-*-*-*-*-*-*-* 1. Salesforce > Update Cases Information *-*-*-*-*-*-*-*-* ##
        """
            1.1 Load `logs` from `Control Center` > CaseLogs
            1.2 Keep only logs of the current week (idx = 0)
            1.3 Retrieve all the cases from SF in a chunkify way
            1.4 Update all cases (Status, L4,L5)
            1.5 Retrieve all the restaurants that should be checked status ~ {"New", "In Progress", "Opened: In Progress"}

        """

        def read_chunkify(case_ids):
            cases = pd.DataFrame()
            case_ids_chunked = chunkify(case_ids, 50)
            for case_ids_chunk in tqdm(case_ids_chunked, total = len(case_ids_chunked)) : 
                cases_chunk = self.salesforce_api.query(f"SELECT Restaurant_UUID__c,Id,OwnerId,Status,Level_4__c,Level_5__c "
                                                   f"FROM Case WHERE Id IN {tuple(case_ids_chunk)}")
                cases = pd.concat([cases,cases_chunk])
            cases = cases.reset_index()
            return cases

        def preprocess_logs(logs) : 
            logs["week_idx"] = logs["week_idx"].astype(int)
            logs             = logs.drop_duplicates(subset = ["id"], keep = "first")
            logs             = logs.dropna(subset = ["status"])
            return logs
        
        def select_logs(logs, week_idx = 0) :
            return logs[logs["week_idx"] == week_idx]

        def update_logs(logs, cases):
            logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
            for idx, row in tqdm(cases.iterrows() , total = len(cases)):
                logs.loc[logs['id'] == row['Id'], 'status']     = row['Status']
                logs.loc[logs['id'] == row['Id'], 'level_4__c'] = row['Level_4__c']
                logs.loc[logs['id'] == row['Id'], 'level_5__c'] = row['Level_5__c']
            return logs

        
        def check_status(logs) : 
            logs["check_status"] = logs.apply(lambda x : x["level_4__c"] in ["", " ", None] , axis = 1)
            return logs

        all_logs = self.data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_logs)
        all_logs = preprocess_logs(all_logs)
        logs     = select_logs(all_logs, week_idx = 0)
        cases    = read_chunkify(case_ids = list(logs["id"].values))
        logs     = update_logs(logs, cases)
        logs     = check_status(logs)

        
        print(f"[No. of Restaurants] [Initially] = {len(logs)}")

        # --------------------------------------------------------------------------------------------------- #
        ## *-*-* 2. Queryrunner > Retrieve info for the restaurants to be checked  *-*-* ##
        """
            2.1 Retrieve all the resto_uuids that should be checked (a) L4 = empty (b) week_idx = 0 (current week)
            2.2 Retrieve Onboarding status for `restos_checking`
            2.3 Retrieve Live orders for `restos_checking` by chunking them 
                - Chunk the `restos_checking` into chunks of size 50 
                - Execute and retrieve the live orders for the chunk into `orders_chunk`
                - Append `orders_chunk` into the final orders dataframe `orders`
        """

        resto_uuids_checking = list(logs.loc[ logs["check_status"] == True, "restaurant_uuid__c"].values)
        print(f"[No. of Restaurants] [To be checked] = {len(resto_uuids_checking)}")

        ## 2.1 [Check] Onboarding / Activated on Wok
        onboarding_status = self.data_loader.load_data_from_query_atlantis(
            report_id = report_id_resto_onboarding, 
            params    = {"restaurant_uuids" : "'" + "','".join(resto_uuids_checking) + "'"}
        )

        ## 2.2 [Check] Taking Trips 
        resto_uuids_checking_chunked = chunkify(resto_uuids_checking, 50)
        orders = pd.DataFrame()

        for chunk in  tqdm(resto_uuids_checking_chunked, total = len(resto_uuids_checking_chunked)) : 
            orders_chunk = self.data_loader.load_data_from_query_neutrino(
                report_id = report_id_restos_live, 
                params    = {"restaurant_uuids" : "'" + "','".join(chunk) + "'"}
            )
            orders = pd.concat([orders, orders_chunk])


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

        sf_df_report = self.salesforce_api.bulk_operation(
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

        all_logs[all_logs["week_idx"] == 0] = logs

        # --------------------------------------------------------------------------------------------------- #

        ## *-*-* 5. Data Loader > Write ALL logs  *-*-* ##
        """
            5.1 Save logs locally
            5.2 Write Logs to kirby table
            5.3 Write logs to Control Center > CurrentCasesLogs
        """
        all_logs.to_csv(
            path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
            index       = False
        )
        self.data_loader.write_data_to_kirby(
            df          = all_logs, 
            table_name  = kirby_tb_restos, 
            casting_map = kirby_casting_map_restos, 
            file_path   = fn_path_restos_logs.format(today.strftime("%Y_%m_%d"))
        )
        self.data_loader.clear_google_sheets_tab(
            cc_id, 
            cc_tab_logs
        )
        self.data_loader.write_data_to_google_sheets(
            all_logs, 
            cc_id, 
            cc_tab_logs,
            spreadsheet_has_headers = True
        )

        
    def run_cases_preparation_v3(self) : 
        ## *-*-* Configuration (attributes) *-*-* #
        today                      = (dt.datetime.now() - dt.timedelta(days = self.args.days_diff))
        cc_id                      = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_logs                = str(mk1.config.get("google_sheets","cc_tab_logs"))
        fn_path_restos_logs        = str(mk1.config.get("app_storage","chrun_restaurants_logs"))
        kirby_tb_restos            = str(mk1.config.get("kirby", "churn_restaurants_table_name"))
        kirby_casting_map_restos   = churn_restaurants_casting_map # from utils

        ## *-*-* 1. Salesforce > Update Status *-*-* ##
        """
            1.1 Load `logs` from `Control Center` > CaseLogs
            1.2 All Logs operations (a) remove logs with week_idx = -2 (b) move week_idx = -1 to week_idx = -2 
            1.2 Retrieve all the cases from SF in a chunkify way
            1.3 Update all cases Status
            1.4 Retrieve all the restaurants that should be checked status ~ {"New", "In Progress", "Opened: In Progress"}
        """

        def read_chunkify(case_ids):
            cases = pd.DataFrame()
            case_ids_chunked = chunkify(case_ids, 50)
            for case_ids_chunk in tqdm(case_ids_chunked, total = len(case_ids_chunked)) : 
                cases_chunk = self.salesforce_api.query(f"SELECT Id,OwnerId,Status,Level_4__c,Level_5__c "
                                                   f"FROM Case WHERE Id IN {tuple(case_ids_chunk)}")
                cases = pd.concat([cases, cases_chunk])
            cases = cases.reset_index()
            return cases
        
        def preprocess_logs(logs) : 
            logs["week_idx"] = logs["week_idx"].astype(int)
            logs             = logs.drop_duplicates(subset = ["id"], keep = "first")
            logs             = logs.dropna(subset = ["status"])
            return logs

        def select_logs(logs, week_idx = 0) :
            return logs[logs["week_idx"] == week_idx]

        def update_logs(logs, cases):
            logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
            for idx, row in tqdm(cases.iterrows() , total = len(cases)):
                logs.loc[logs['id'] == row['Id'], 'status']     = row['Status']
                logs.loc[logs['id'] == row['Id'], 'level_4__c'] = row['Level_4__c']
                logs.loc[logs['id'] == row['Id'], 'level_5__c'] = row['Level_5__c']
            return logs

        # ------ All Logs (week = -2, -1, 0)

        all_logs = self.data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_logs)
        all_logs = preprocess_logs(all_logs)

        # ------ Previous Logs (week = -2, -1)
        all_logs = all_logs[all_logs["week_idx"] != -2]
        all_logs.loc[all_logs["week_idx"] == -1, "week_idx"] = -2
        all_logs.loc[all_logs["week_idx"] == 0, "week_idx"]  = -1

        
        # ------- Current Logs (week = 0)
        logs  = select_logs(all_logs, week_idx = -1)
        cases = read_chunkify(case_ids = list(logs["id"].values))
        logs  = update_logs(logs,cases)

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

        sf_df_report = self.salesforce_api.bulk_operation(
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
        all_logs[all_logs["week_idx"] == -1] = logs # NEW command

        # --------------------------------------------------------------------------------------------------- #

        ## *-*-* 3. Data Loader > Write ALL logs  *-*-* ##
        """
            5.1 Save logs locally
            5.2 Write Logs to kirby table
            5.3 Write logs to Control Center > PreviousCasesLogs
        """
        all_logs.to_csv(
            path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
            index       = False
        )
        self.data_loader.write_data_to_kirby(
            df          = all_logs, 
            table_name  = kirby_tb_restos, 
            casting_map = kirby_casting_map_restos, 
            file_path   = fn_path_restos_logs.format(today.strftime("%Y_%m_%d"))
        )

        self.data_loader.clear_google_sheets_tab(
            cc_id, 
            cc_tab_logs
        )

        self.data_loader.write_data_to_google_sheets(
            all_logs, 
            cc_id, 
            cc_tab_logs,
            spreadsheet_has_headers = True
        )


    

    def run_cases_creation_v3(self) :
        ## *-*-* Configuration (attributes) *-*-* #
        today                    = (dt.datetime.now() - dt.timedelta(days = self.args.days_diff))
        cc_id                    = str(mk1.config.get("google_sheets","cc_id"))
        cc_tab_countries         = str(mk1.config.get("google_sheets","cc_tab_countries"))
        cc_tab_resto_exclusions  = str(mk1.config.get("google_sheets","cc_tab_resto_exclusions"))
        cc_tab_logs              = str(mk1.config.get("google_sheets","cc_tab_logs"))
        report_id_restos         = str(mk1.config.get("queryrunner","churn_restaurants_report_id"))
        fn_path_restos           = str(mk1.config.get("app_storage","chrun_restaurants"))
        fn_path_restos_logs      = str(mk1.config.get("app_storage","chrun_restaurants_logs"))
        kirby_tb_restos          = str(mk1.config.get("kirby", "churn_restaurants_table_name"))
        kirby_casting_map_restos = churn_restaurants_casting_map # from utils

        # ------------------------------------------------------------------------------------------------------------------------ #
        ## *-*-* 1. Data Loader > Load `restos` data from queryrunner atlantis *-*-* ##
        """
            1.1 Load all logs from 'CaseLogs' tab at `all_logs` dataframe
            1.2 Update information about (L4,L5, Status)
            1.2 Load the dataframe after executing the query for the cases
            1.3 Keep only those that do not have empty values in 
                (`restaurant_segment`, `restaurant_category`, `restaurant_direct`, `accountId`)

        """
        def read_chunkify(case_ids):
            cases = pd.DataFrame()
            case_ids_chunked = chunkify(case_ids, 50)
            for case_ids_chunk in tqdm(case_ids_chunked, total = len(case_ids_chunked)) : 
                cases_chunk = self.salesforce_api.query(f"SELECT Id,OwnerId,Status,Level_4__c,Level_5__c FROM Case WHERE Id IN {tuple(case_ids_chunk)}")
                cases = pd.concat([cases, cases_chunk])
            cases = cases.reset_index()
            return cases

        all_logs = self.data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_logs)
        all_logs["week_idx"]               = all_logs["week_idx"].astype(int)
        case_ids                           = list(all_logs["id"].values)
        cases                              = read_chunkify(case_ids)
        all_logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
        all_logs["status"]                 = cases["Status"]
        all_logs["level_4__c"]             = cases["Level_4__c"]
        all_logs["level_5__c"]             = cases["Level_5__c"]


        if not os.path.exists(fn_path_restos.format(today.strftime("%Y_%m_%d"))) :
            restos = self.data_loader.load_data_from_query_atlantis(
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
        countries_scheduler   = self.data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_countries)
        countries_scheduler   = countries_scheduler.rename({"Country" : "country_name"}, axis = 1)
        restos_to_be_excluded = self.data_loader.load_data_from_google_sheets_tab(cc_id, cc_tab_resto_exclusions)


        ## *-*-* 3. DataFrame opertations > Combine `countries_scheduler` and `restos`  *-*-* ##
        """
            3.1 Merge `countries_scheduler` and `restos` 
            3.2 Filtering based on :
                - The filter given for Restaurant (Segment, Category, Direct) 
                - Remove restaurants that should be excluded in any case
                - Remove restaurants that were 'Case Actioned' The last 14 days
        """
        def filtering(row) : 
            check_segment           = row[row["restaurant_segment"]]  == "TRUE"
            check_category          = row[row["restaurant_category"]] == "TRUE"
            check_direct            = row[row["restaurant_direct"]]   == "TRUE"
            check_uuid              = row["restaurant_uuid"] not in list(restos_to_be_excluded[row["country_name"]].values)
            check_not_existing_14d  = row["restaurant_uuid"] not in list(all_logs["restaurant_uuid__c"].values)
            check_case_actioned_14d = row["restaurant_uuid"] in list(all_logs["restaurant_uuid__c"].values) and \
                            ~all_logs.loc[all_logs["restaurant_uuid__c"] == row["restaurant_uuid"], "level_4__c"].str.contains('Case Actioned').any()

            return True if (check_segment and check_category and check_direct and  check_uuid and (check_not_existing_14d or check_case_actioned_14d)) else False


        print(f"[No. of Restaurants] [Initially] = {len(restos)}")
        restos_expanded = restos.merge(countries_scheduler, on = 'country_name')
        restos_expanded["restaurant_name"] = restos_expanded["restaurant_name"].apply(lambda x: x.encode('utf-8'))
        restos_expanded["Keep Restaurant"] = restos_expanded.apply(lambda x : filtering(x), axis = 1) # for Bulk SF API
        restos_expanded = restos_expanded[restos_expanded["Keep Restaurant"] == True]
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
        sf_df["Level_2__c"]         = "Account & Settings"
        sf_df["Level_3__c"]         = "Churn Re-engagement"
        sf_df["Level_4__c"]         = ""
        sf_df["Level_5__c"]         = ""

        sf_df_report = self.salesforce_api.bulk_operation(
            sobject_data_df = sf_df,
            sobject         = "Case",
            sobject_id_type = "Id",
            operation       = "insert",
            seconds         = 5

        )


        ## --------- Logs
        logs = sf_df_report.copy()
        logs = logs[logs["status"] != "Failed"]
        logs["week_idx"] = 0
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

        logs = pd.merge(
            left = logs, 
            right = restos_expanded[[
                "restaurant_uuid__c",
                "country_name", 
                "restaurant_segment", 
                "restaurant_category", 
                "restaurant_direct", 
                "restaurant_name"
            ]] , 
            on  = "restaurant_uuid__c", 
            how = "inner"
        )
        logs["restaurant_name"]        = logs["restaurant_name"].apply(lambda x: x.decode('utf-8'))
        logs["creation_date"]          = today.strftime("%Y-%m-%d %H:%M:%S") 
        logs["last_modification_date"] = today.strftime("%Y-%m-%d %H:%M:%S")
        logs["status"]                 = "New"
        logs["salesforce_view_link"]   = logs.apply(lambda x : 
            self.salesforce_api.get_request_urls()["production"].format(
                sobject    = "Case",
                sobject_id = x["id"]
            ), 
            axis = 1
        )
    
        logs = logs[[
            "week_idx",
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



        ## *-*-* 5. Data Loader > Write ALL logs  *-*-* ##
        """
            5.1 Save logs locally
            5.2 Write Logs to kirby table
            5.3 Write logs to Control Center > CurrentCaseLogs
        """
        all_logs = pd.concat([all_logs, logs])
        all_logs = all_logs.sort_values(
            by        = 'week_idx', 
            ascending = False
        )

        all_logs.to_csv(
            path_or_buf = fn_path_restos_logs.format(today.strftime("%Y_%m_%d")), 
            index       = False
        )
        self.data_loader.write_data_to_kirby(
            df          = all_logs, 
            table_name  = kirby_tb_restos, 
            casting_map = kirby_casting_map_restos, 
            file_path   = fn_path_restos_logs.format(today.strftime("%Y_%m_%d"))
        )

        self.data_loader.write_data_to_google_sheets(
            all_logs, 
            cc_id, 
            cc_tab_logs,
            spreadsheet_has_headers = True
        )




    ## -------------------------------------------------------------------------------------------------------------------------------------------- ##
    ## -------------------------------------------------------------------------------------------------------------------------------------------- ##
    ## -------------------------------------------------------------------------------------------------------------------------------------------- ##
    def run(self):
        operation = self.args.operation
        
        self.run_initialization()
        self.run_update_logs_from_salesforce_and_file()
        time.sleep(1)

        if operation == "create_cases" : 
            self.run_cases_creation_v3()

        elif operation == "close_cases" : 
            self.run_cases_closing_v3()

        elif operation == "close_cases_backfill" : 
            start_date = self.args.backfill_start_date
            end_date   = self.args.backfill_end_date
            statuses   = self.args.backfill_statuses.split(",") if self.args.backfill_statuses != '' else []
            self.run_cases_closing_backfill(start_date, end_date, statuses)

        elif operation == "prepare_cases" : 
            self.run_cases_preparation_v3()
        

if __name__ == '__main__':

    mk1        = MkI.get_instance(_logging = True)
    controller = Controller(mk1)
    controller.run()