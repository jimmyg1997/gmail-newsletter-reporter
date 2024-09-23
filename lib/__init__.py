#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on 11/07/2022
@author: Dimitrioss Georgiou
"""
import yaml
import os



# try:
#     env_path = "config/environment.yaml"
#     with open(env_path, "r") as env_file:
#         env_file    = yaml.load(env_file.read(), yaml.FullLoader)
#         ENVIRONMENT = env_file["environment"]
        
# except FileNotFoundError as e:
#     print(f"{env_path} does not exist. This file needs to be set up manually and ignored from git")
#     raise e
    
# except KeyError as e:
#     print(f"{env_path} is missing {e} and that's the only value it needs")
#     raise e
    
    
# _secrets_path = os.path.join("secrets/", ENVIRONMENT, "secrets.yaml")
# _config_path  = os.path.join("config/", ENVIRONMENT, "config.yaml")


# # Load the paths
# _secrets_path  = os.path.join("secrets/", ENVIRONMENT, "secrets.yaml")
# with open(_secrets_path, "r") as secrets_file:
#     secrets = yaml.load(secrets_file.read(), yaml.FullLoader)
    
# with open(_config_path, "r") as config_file:
#     config = yaml.load(config_file.read(), yaml.FullLoader)


