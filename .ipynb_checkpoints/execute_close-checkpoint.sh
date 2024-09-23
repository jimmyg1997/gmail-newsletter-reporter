#!/usr/bin/env python3
source /home/$(whoami)/$(whoami)_nfs/envs/env_churn_program/bin/activate
cd     /home/$(whoami)/$(whoami)_nfs/production/krakow_ops_enablement/EMEA_EATS/dimitrios/churn_program
python3 main_churn.py --operation close_cases

