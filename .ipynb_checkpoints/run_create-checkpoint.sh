#!/usr/bin/env python3
source /home/$(whoami)/$(whoami)_nfs/production/krakow_ops_enablement/EMEA_EATS/dimitrios/churn_program/venv/bin/activate
cd     /home/$(whoami)/$(whoami)_nfs/production/krakow_ops_enablement/EMEA_EATS/dimitrios/churn_program
python3 main_churnV3.py --operation create_cases
