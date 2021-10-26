#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2021, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings, subprocess, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API to either get current BIOS boot mode and boot order or change BIOS boot order")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='GetSetBootOrderBootSourceStateREDFISH.py -ip 192.168.0.120 -u root -p calvin -r y, this example will get current BIOS boot mode and the boot order. GetSetBootOrderBootSourceStateREDFISH.py -ip 192.168.0.120 -u root -p calvin -r y -s BIOS.Setup.1-1#UefiBootSeq#NIC.PxeDevice.1-1#9d0c81c0539f5ccc019510686dd6f525, this example will reboot the server now to change the boot order and set NIC.PXeDevice.1-1 as first device in the boot order. GetSetBootOrderBootSourceStateREDFISH.py -ip 192.168.0.120 -u root -p calvin -r y -s BIOS.Setup.1-1#UefiBootSeq#NIC.PxeDevice.1-1#9d0c81c0539f5ccc019510686dd6f525,BIOS.Setup.1-1#UefiBootSeq#Disk.SDInternal.1-1#e7a82d497a82880f7000a631ed48e5ec,BIOS.Setup.1-1#UefiBootSeq#Disk.SATAEmbedded.C-1#d3baa28d14ae28d4b1a6a2115fef8bfe, this example shows rebooting the server now to change the boot order to first device as NIC.Pxe.1-1, second device as SD card and third device as SATA disk.')
parser.add_argument('-g', help='Get current BIOS boot mode and boot order, pass in \"y\"', required=False)
parser.add_argument('-s', help='Set BIOS boot order, pass in the ID string of the device. If you only pass in one ID string, this will move this device to first device in the boot order. If passing in multiple devices to change the boot order, use comma separator between each device. Example of valid string ID to pass in: BIOS.Setup.1-1#UefiBootSeq#NIC.PxeDevice.1-1#9d0c81c0539f5ccc019510686dd6f525', required=False)
parser.add_argument('-r', help='Reboot the server to execute BIOS config job. Pass in \"y\" to reboot the server now or \"n\" not to reboot the server. If you select to not reboot the server now, config job is still marked as scheduled and will execute on next server manual reboot', required=False)

args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]

### Function to check if iDRAC version detected is supported for this feature using Redfish

def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootSources' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, unable to access iDRAC, check to make sure you are passing in valid iDRAC credentials")
        sys.exit()
    if response.status_code == 200 or response.status_code == 202:
        pass
    else:
        print("\n- FAIL, iDRAC version detected does not support this feature, status code %s returned" % response.status_code)
        sys.exit()

### Function to get BIOS current boot mode

def get_bios_boot_mode():
    global current_boot_mode
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Bios' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    current_boot_mode = data['Attributes']["BootMode"]
                    
### Function to get current boot devices and their boot source state

def get_bios_boot_source_state():
    global boot_seq
    global boot_device_list_from_file
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/BootSources' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if current_boot_mode == "Uefi":
        print("\n- Current %s boot order \n" % current_boot_mode)
        for i in data["Attributes"]["UefiBootSeq"]:
            for ii in i.items():
                print("%s: %s" % (ii[0], ii[1]))
            print("\n")
    elif current_boot_mode == "Bios":
        print("\n- Current %s boot order \n" % current_boot_mode)
        for i in data["Attributes"]["BootSeq"]:
            for ii in i.items():
                print("%s: %s" % (ii[0], ii[1]))
            print("\n")
    sys.exit()


### Function to set BIOS pending value(s) for either boot order or boot source state

def set_bios_boot_source_state():
    url = 'https://%s/redfish/v1/Systems/System.Embedded.1/BootSources/Settings' % idrac_ip
    headers = {'content-type': 'application/json'}
    if "," in args["s"]:
        boot_devices = args["s"].split(",")
    else:
        boot_devices = []
        boot_devices.append(args["s"])    
    if current_boot_mode == "Uefi":
        payload = {'Attributes':{'UefiBootSeq': []}}
        index_count = 0
        for i in boot_devices:
            payload["Attributes"]["UefiBootSeq"].append({"Index": index_count, "Id": i})
            index_count+=1
    elif current_boot_mode == "Bios":
        payload = {'Attributes':{'BootSeq': []}}
        index_count = 0
        for i in boot_devices:
            payload["Attributes"]["BootSeq"].append({"Index": index_count, "Id": i})
            index_count+=1
    response = requests.patch(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    data=response.json()
    statusCode = response.status_code
    if statusCode == 200:
        print("\n- PASS: PATCH command passed to set pending boot order changes.")
    else:
        print("\n- FAIL, PATCH command failed, errror code is %s" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()

### Function to create BIOS target config job

def create_bios_config_job():
    global job_id
    url = 'https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs' % idrac_ip
    payload = {"TargetSettingsURI":"/redfish/v1/Systems/System.Embedded.1/Bios/Settings"}
    headers = {'content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username, idrac_password))
    statusCode = response.status_code
    
    if statusCode == 200:
        print("- PASS: POST command passed to create target config job, status code 200 returned.")
    else:
        print("- FAIL, POST command failed to create BIOS config job, status code is %s\n" % statusCode)
        detail_message=str(response.__dict__)
        print(detail_message)
        sys.exit()
    convert_to_string=str(response.__dict__)
    jobid_search=re.search("JID_.+?,",convert_to_string).group()
    job_id=re.sub("[,']","",jobid_search)
    print("- INFO %s job ID successfully created\n" % job_id)
    
### Function to verify job is marked as scheduled before rebooting the server
    
def check_job_status_schedule():
    while True:
        req = requests.get('https://%s/redfish/v1/TaskService/Tasks/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        statusCode = req.status_code
        if statusCode == 202 or statusCode == 200:
            pass
            time.sleep(10)
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if data['Messages'][0]['Message'] == "Task successfully scheduled.":
            print("- PASS, job ID successfully marked as scheduled")
            break
        if "Lifecycle Controller in use" in data['Messages'][0]['Message']:
            print("- INFO, Lifecycle Controller in use, this job will start when Lifecycle Controller is available. Check overall jobqueue to make sure no other jobs are running and make sure server is either off or out of POST")
            sys.exit()
        else:
            print("- INFO: JobStatus not scheduled, current status is: %s" % data['Messages'][0]['Message'])

def reboot_server():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- INFO, Current server power state is: %s" % data['PowerState'])
    if data['PowerState'] == "On":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'GracefulShutdown'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, POST command passed to gracefully power OFF server, status code return is %s" % statusCode)
            print("- INFO, script will now verify the server was able to perform a graceful shutdown. If the server was unable to perform a graceful shutdown, forced shutdown will be invoked in 5 minutes")
            time.sleep(15)
            start_time = datetime.now()
        else:
            print("\n- FAIL, Command failed to gracefully power OFF server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
        while True:
            response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
            data = response.json()
            current_time = str(datetime.now() - start_time)[0:7]
            if data['PowerState'] == "Off":
                print("- PASS, GET command passed to verify graceful shutdown was successful and server is in OFF state")
                break
            elif current_time == "0:05:00":
                print("- INFO, unable to perform graceful shutdown, server will now perform forced shutdown")
                payload = {'ResetType': 'ForceOff'}
                headers = {'content-type': 'application/json'}
                response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
                statusCode = response.status_code
                if statusCode == 204:
                    print("- PASS, POST command passed to perform forced shutdown, status code return is %s" % statusCode)
                    time.sleep(15)
                    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
                    data = response.json()
                    if data['PowerState'] == "Off":
                        print("- PASS, GET command passed to verify forced shutdown was successful and server is in OFF state")
                        break
                    else:
                        print("- FAIL, server not in OFF state, current power status is %s" % data['PowerState'])
                        sys.exit()    
            else:
                continue
            
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, status code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    elif data['PowerState'] == "Off":
        url = 'https://%s/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset' % idrac_ip
        payload = {'ResetType': 'On'}
        headers = {'content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, auth=(idrac_username,idrac_password))
        statusCode = response.status_code
        if statusCode == 204:
            print("- PASS, Command passed to power ON server, code return is %s" % statusCode)
        else:
            print("\n- FAIL, Command failed to power ON server, status code is: %s\n" % statusCode)
            print("Extended Info Message: {0}".format(response.json()))
            sys.exit()
    else:
        print("- FAIL, unable to get current server power state to perform either reboot or power on")
        sys.exit()


def check_final_job_status():
    start_time=datetime.now()
    time.sleep(1)
    while True:
        check_idrac_connection()
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=str((datetime.now()-start_time))[0:7]
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "0:30:00":
            print("\n- FAIL: Timeout of 30 minutes has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or "fail" in data['JobState'] or "Fail" in data['JobState']:
            print("- FAIL: %s failed" % job_id)
            sys.exit()
        
        elif "completed successfully" in data['Message']:
            print("\n- PASS, job ID %s successfully marked completed" % job_id)
            print("\n- Final detailed job results -\n")
            for i in data.items():
                print("%s: %s" % (i[0], i[1]))
            print("\n- JOB ID %s completed in %s" % (job_id, current_time))
            sys.exit()
        else:
            print("- INFO, JobStatus not completed, current status: \"%s\", execution time: \"%s\"" % (data['Message'], current_time))
            check_idrac_connection()
            time.sleep(5)


def check_idrac_connection():
    ping_command="ping %s -n 5" % idrac_ip
    while True:
        try:
            ping_output = subprocess.Popen(ping_command, stdout = subprocess.PIPE, shell=True).communicate()[0]
            ping_results = re.search("Lost = .", ping_output).group()
            if ping_results == "Lost = 0":
                break
            else:
                print("\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 3 minutes")
                time.sleep(180)
        except:
            ping_output = subprocess.run(ping_command,universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if "Lost = 0" in ping_output.stdout:
                break
            else:
                print("\n- INFO, iDRAC connection lost due to slow network connection or component being updated requires iDRAC reset. Script will recheck iDRAC connection in 3 minutes")
                time.sleep(180)



### Run code

if __name__ == "__main__":
    if args["g"]:
        get_bios_boot_mode()
        get_bios_boot_source_state()
    elif args["s"]:
        get_bios_boot_mode()
        set_bios_boot_source_state()
        create_bios_config_job()
        check_job_status_schedule()
        if args["r"] == "y":
            print("- INFO, user selected to reboot the server now to execute BIOS config job")
            reboot_server()
            check_final_job_status()
        elif args["r"] == "n":
            print("- INFO, user selected to not reboot the server to execute the config job. Job ID is still scheduled and will execute on next server manual reboot.")
        else:
            print("- INFO, either missing reboot argument or invalid value passed in. Job ID is still scheduled and will execute on next server manual reboot.")
    else:
        print("\n- FAIL, either missing parameter(s) or incorrect parameter(s) passed in. If needed, execute script with -h for script help")


