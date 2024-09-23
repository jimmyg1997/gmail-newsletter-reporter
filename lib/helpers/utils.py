# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    [*] Description : Utilities Functions for the current automation
    [*] Author      : dgeorgiou3@gmail.com
    [*] Date        : Jan, 2024
    [*] Links       :
"""

import os, ssl, stat, subprocess, sys
import os.path
from itertools import zip_longest
from typing import Dict, Any, List
import pandas as pd

STAT_0o775 = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
             | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP
             | stat.S_IROTH |                stat.S_IXOTH )


# -*-*-*-*-*-*-*-*-*-*-* #
#       FUNCTIONS        #
# -*-*-*-*-*-*-*-*-*-*-* #
def install_certifi():
    openssl_dir, openssl_cafile = os.path.split(
        ssl.get_default_verify_paths().openssl_cafile)

    print(" -- pip install --upgrade certifi")
    subprocess.check_call([sys.executable,
        "-E", "-s", "-m", "pip", "install", "--upgrade", "certifi"])

    import certifi

    # change working directory to the default SSL directory
    os.chdir(openssl_dir)
    relpath_to_certifi_cafile = os.path.relpath(certifi.where())
    print(" -- removing any existing file or link")
    try:
        os.remove(openssl_cafile)
    except FileNotFoundError:
        pass
    print(" -- creating symlink to certifi certificate bundle")
    os.symlink(relpath_to_certifi_cafile, openssl_cafile)
    print(" -- setting permissions")
    os.chmod(openssl_cafile, STAT_0o775)
    print(" -- update complete")

def chunkify(lst, size):
    args = [iter(lst)] * size
    return [[elem for elem in t if elem is not None] for t in zip_longest(*args)]
