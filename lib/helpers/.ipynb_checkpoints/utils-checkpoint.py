# -*-*-*-*-*-*-*-*-*-*-* #
#       VARIABLES        #
# -*-*-*-*-*-*-*-*-*-*-* #

churn_restaurants_casting_map = {
    "week_idx"               : int,
    "creation_date"          : "datetime64[ns]",
    "last_modification_date" : "datetime64[ns]",
    "status"                 : str,
    "salesforce_view_link"   : str,
    "subject"                : str,
    "id"                     : str,
    "onwer_id"               : str,
    "account_id"             : str,
    "restaurant_uuid__c"     : str,
    "origin"                 : str,
    "type"                   : str,
    "record_type_id"         : str,
    "kpi__c"                 : str,
    "project_type__c"        : str,
    "level_2__c"             : str,
    "level_3__c"             : str,
    "level_4__c"             : str,
    "level_5__c"             : str,
    "country_name"           : str,
    "restaurant_segment"     : str,
    "restaurant_category"    : str,
    "restaurant_direct"      : str,
    "restaurant_name"        : str,
    
}




# -*-*-*-*-*-*-*-*-*-*-* #
#       FUNCTIONS        #
# -*-*-*-*-*-*-*-*-*-*-* #
from itertools import zip_longest

def chunkify(lst, size):
    args = [iter(lst)] * size
    return [[elem for elem in t if elem is not None] for t in zip_longest(*args)]