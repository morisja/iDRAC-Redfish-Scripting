#!/usr/bin/python3
#
#_author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 8.0
#
# Copyright (c) 2022, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Python module for iDRAC Redfish support to perform multiple workflows. 

import base64
import getpass
import json
import logging
import os
import re
import requests
import sys
import time
import warnings

from datetime import datetime
from pprint import pprint
from idrac_manager import IdracManager, IdracManagerException

warnings.filterwarnings("ignore")
logging.basicConfig(format='%(message)s', stream=sys.stdout, level=logging.INFO)

def get_storage_controllers(script_examples=""):
    """Function to get server storage controller FQDDs"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_storage_controllers(), this example will return current storage controller FQDDs detected. These FQDDs can be used to execute other storage functions to get physcial disks, virtual disks, reset controller are some examples.")
        return
    im=IdracManager(creds)
    try:
        data = im.get_storage_controllers()
        print("\n- Server controller(s) detected -\n")
        controller_list = []
        for i in data['Members']:
            for ii in i.items():
                controller = ii[1].split("/")[-1]
                controller_list.append(controller)
                print(controller)
    except IdracManagerException as e:
        logging.error(e)

def get_storage_controller_details(script_examples="", controller_fqdd=""):
    """Function to get details for a specific storage controller. Supported function argument: controller_fqdd"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_storage_controller_details(controller_fqdd='RAID.Integrated.1-1'), this example will return detailed information for storage controller RAID.Integrated.1-1")
        return
    im=IdracManager(creds)
    try:
        im.get_storage_controller_detail(controller_fqdd)
        data = response.json()
        logging.info("\n - Detailed controller information for %s -\n" % controller_fqdd)
        for i in data.items():
            pprint(i)
    except IdracManagerException as e:
        logging.error(e)

def get_storage_disks(script_examples="", controller_fqdd=""):
    """Function to get drive FQDDs for storage controller. Supported function argument: controller_fqdd"""
    if script_examples:
        print("\n- IdracRedfishSupport.get_storage_disks(controller_fqdd='RAID.Integrated.1-1'), this example will return disk FQDDs detected for storage controller RAID.Integrated.1-1")
        return
    im=IdracManager(creds)

    try:
        response=im.get_storage_controller_detail(controller_fqdd)
        data = response.json()
        drive_list=[]
        if not data['drives']:
            logging.warning("\n- WARNING, no drives detected for %s" % controller_fqdd)
            return
        logging.info("\n- Drive(s) detected for %s -\n" % controller_fqdd)
        for i in data['Drives']:
            id=i['@odata.id'].split("/")[-1]
            drive_list.append(id)
            response=im.get_physical_drive(id)
   
            data = response.json()
            print(i['@odata.id'].split("/")[-1])
    except IdracManagerException as e:
        logger.error(e)

