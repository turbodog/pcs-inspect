#!/usr/bin/env python

import argparse
import json
import os
import requests
from requests.exceptions import RequestException
import sys

##########################################################################################
# Configuration
##########################################################################################

pc_parser = argparse.ArgumentParser(description='This script collects or processes Policies and Alerts.', prog=os.path.basename(__file__))

pc_parser.add_argument(
    '-c', '--customer_name',
    type=str, required=True,
    help='*Required* Customer Name, used for Alert and Policy files')

pc_parser.add_argument('-m', '--mode',
    type=str, required=True, choices=['collect', 'process'],
    help="*Required* Mode: collect Policies and Alerts, or process collected data.")

pc_parser.add_argument('-u', '--url',
    type=str,
    help="(Required with '--mode collect') Prisma Cloud API URL")

pc_parser.add_argument('-a', '--access_key',
    type=str,
    help="(Required with '--mode collect') API Access Key")

pc_parser.add_argument('-s', '--secret_key',
    type=str,
    help="(Required with '--mode collect') API Secret Key")

pc_parser.add_argument('-ca', '--cloud_account',
    type=str,
    help='(Optional) Cloud Account ID to limit the Alert query')

pc_parser.add_argument('-ta', '--time_range_amount',
    type=int, default=1, choices=[1, 2, 3],
    help="(Optional) Time Range Amount to limit the Alert query. Default: 1")

pc_parser.add_argument('-tu', '--time_range_unit',
    type=str, default='month', choices=['day', 'week', 'month', 'year'],
    help="(Optional) Time Range Unit to limit the Alert query. Default: 'month'")

pc_parser.add_argument('-d', '--debug',
    action='store_true',
    help='(Optional) Enable debugging.')

args = pc_parser.parse_args()

####

DEBUG_MODE = args.debug

RUN_MODE = args.mode
PRISMA_API_ENDPOINT = args.url        # or os.environ.get('PRISMA_API_ENDPOINT')
PRISMA_ACCESS_KEY   = args.access_key # or os.environ.get('PRISMA_ACCESS_KEY')
PRISMA_SECRET_KEY   = args.secret_key # or os.environ.get('PRISMA_SECRET_KEY')
PRISMA_API_HEADERS = {
    'Accept': 'application/json; charset=UTF-8',
    'Content-Type': 'application/json'
}
PRISMA_API_REQUEST_TIMEOUTS = (30, 300) # (CONNECT, READ)
CUSTOMER_NAME = args.customer_name
CLOUD_ACCOUNT_ID = args.cloud_account
POLICY_FILE = '%s-policies.txt' % CUSTOMER_NAME
ALERT_FILE = '%s-alerts.txt' % CUSTOMER_NAME
TIME_RANGE_AMOUNT = args.time_range_amount
TIME_RANGE_UNIT = args.time_range_unit
TIME_RANGE_LABEL = 'Time Range - Past %s %s' % (TIME_RANGE_AMOUNT, TIME_RANGE_UNIT.capitalize()) 

##########################################################################################
# Utilities.
##########################################################################################

def make_api_call(method, url, requ_data = None):
    try:
        requ = requests.Request(method, url, data = requ_data, headers = PRISMA_API_HEADERS)
        prep = requ.prepare()
        sess = requests.Session()
        resp = sess.send(prep, timeout=(PRISMA_API_REQUEST_TIMEOUTS))
        if resp.status_code == 200:
            return resp.content
        else:
            return {}
    except RequestException as e:
        print('Error with API: %s: %s' % (url, str(e)))
        sys.exit()

####

def get_prisma_login():
    request_data = json.dumps({
        "username": PRISMA_ACCESS_KEY,
        "password": PRISMA_SECRET_KEY
    })
    api_response = make_api_call('POST', '%s/login' % PRISMA_API_ENDPOINT, request_data)
    resp_data = json.loads(api_response)
    token = resp_data.get('token')
    if not token:
        print('Error with API Login: %s' % resp_data)
        sys.exit()
    return token

####

def get_policies():
    api_response = make_api_call('GET', '%s/policy?policy.enabled=true' % PRISMA_API_ENDPOINT)
    policy_file = open(POLICY_FILE, 'w') 
    policy_file.write(api_response)
    policy_file.close()

####

def get_alerts():
    body_params = {"timeRange": {"value": {"unit":"%s" % TIME_RANGE_UNIT, "amount":TIME_RANGE_AMOUNT}, "type":"relative"}}
    if CLOUD_ACCOUNT_ID:
        body_params["filters"] = [{"name":"cloud.accountId","value":"%s" % CLOUD_ACCOUNT_ID, "operator":"="}]
    request_data = json.dumps(body_params)
    api_response = make_api_call('POST', '%s/alert' % PRISMA_API_ENDPOINT, request_data)
    alert_file = open(ALERT_FILE, 'w') 
    alert_file.write(api_response)
    alert_file.close()

##########################################################################################
##########################################################################################
# Collect mode: Query the API and write the results to files.
##########################################################################################
##########################################################################################

if RUN_MODE == 'collect':
    if not PRISMA_API_ENDPOINT:
        print("Error: '--url' is required with '--mode input'")
        sys.exit(0)
    if not PRISMA_ACCESS_KEY:
        print("Error: '--access_key' is required with '--mode input'")
        sys.exit(0)
    if not PRISMA_SECRET_KEY:
        print("Error: '--secret_key' is required with '--mode input'")
        sys.exit(0)

    print('Generating Prisma Cloud API Token')
    token = get_prisma_login()
    if DEBUG_MODE:
        print
        print(token)
        print
    PRISMA_API_HEADERS['x-redlock-auth'] = token
    print

    print('Querying Policies')
    get_policies()
    print('Results saved as: %s' % POLICY_FILE)
    print

    print('Querying Alerts')
    get_alerts()
    print('Results saved as: %s' % ALERT_FILE)
    print

    print("Run '%s --customer_name %s --mode process' to process the collected data." % (os.path.basename(__file__), CUSTOMER_NAME))
    print("To save the processed data to a file, redirect the above command by adding ' > {name}-summary.tab'".format(name = CUSTOMER_NAME))
    sys.exit(0)

##########################################################################################
##########################################################################################
# Inspect mode: Read the result files and output summary results.
##########################################################################################
##########################################################################################

##########################################################################################
# Validation.
##########################################################################################

if not os.path.isfile(POLICY_FILE):
    print('Error: Policy file does not exist: %' % POLICY_FILE)
    sys.exit(1)

if not os.path.isfile(ALERT_FILE):
    print('Error: Alert file does not exist: %' % ALERT_FILE)
    sys.exit(1)

##########################################################################################
# Counters and Structures.
##########################################################################################

policy_counts = {
    'high':        0,
    'medium':      0,
    'low':         0,
    'anomaly':     0,
    'audit_event': 0,
    'config':      0,
    'network':     0,
}

# Duplication between the above and below intended for future error checking.

alert_counts = {
    'open':             0,
    'resolved':         0,
    'resolved_deleted': 0,
    'resolved_updated': 0,
    'resolved_high':    0,
    'resolved_medium':  0,
    'resolved_low':     0,
    'shiftable':        0,
    'remediable':       0,
}

policies = {}
alerts_by_compliance_standard = {}
alerts_by_policy = {}

##########################################################################################
# Loop through all Policies and collect the details of each Policy.
##########################################################################################

with open(POLICY_FILE, 'r') as f:
  policy_list = json.load(f)

for policy in policy_list:
    policyId = policy['policyId']
    # Transform Policies from policy_list to policies.
    if not policies.has_key(policyId):
        policies[policyId] = {}
    policies[policyId]['policyName'] = policy['name']
    policies[policyId]['policySeverity'] = policy['severity']
    policies[policyId]['policyType'] = policy['policyType']
    policies[policyId]['policyShiftable'] = 'build' in policy['policySubTypes']
    policies[policyId]['policyRemediable'] = policy['remediable']
    policies[policyId]['policyOpenAlertsCount'] = policy['openAlertsCount']
    # Create sets and lists of Compliance Standards to create a sorted, unique list of counters for each Compliance Standard.
    compliance_standards_set = set()
    policies[policyId]['complianceStandards'] = list()
    if policy.has_key('complianceMetadata'):
        for standard in policy['complianceMetadata']:
            compliance_standards_set.add(standard['standardName'])
        compliance_standards_list = list(compliance_standards_set)
        compliance_standards_list.sort()
        policies[policyId]['complianceStandards'] = compliance_standards_list
    # Initialize Compliance Standard Alert Counts (to avoid an error with += when the variable is undefined).
    for standard in compliance_standards_list:
        if not alerts_by_compliance_standard.has_key(standard):
            alerts_by_compliance_standard[standard] = {'high': 0, 'medium': 0, 'low': 0}


##########################################################################################
# Loop through all Alerts and collect the details of each Alert.
# Some details come from the Alert, some from the associated Policy.
##########################################################################################
  
with open(ALERT_FILE, 'r') as f:
  alert_list = json.load(f)

for alert in alert_list:
    policyId = alert['policy']['policyId']
    policyName = policies[policyId]['policyName']
    # Transform alerts from alert_list to alerts_by_policy, and initialize Alert Count (to avoid an error with += when the variable is undefined).
    if not alerts_by_policy.has_key(policyName):
        alerts_by_policy[policyName] = {'policyId': policyId, 'alertCount': 0}
    # Increment Alert Count for each associated Compliance Standard
    for standard in policies[policyId]['complianceStandards']:
        alerts_by_compliance_standard[standard][policies[policyId]['policySeverity']] += 1
    # Increment Alert Count for associated Policy
    alerts_by_policy[policyName]['alertCount'] += 1
    # Increment Policies by Severity
    policy_counts[policies[policyId]['policySeverity']] += 1
    # Increment Policies by Type
    policy_counts[policies[policyId]['policyType']] += 1
    # Increment Alerts by Status
    alert_counts[alert['status']] += 1
    # Increment Alerts Closed by Reason
    if alert.has_key('reason'):
        if alert['reason'] == 'RESOURCE_DELETED':
            alert_counts['resolved_deleted'] += 1
        if alert['reason'] == 'RESOURCE_UPDATED':
            alert_counts['resolved_updated'] += 1
    # Increment Alerts by Severity
    alert_counts['resolved_%s' % policies[policyId]['policySeverity']] += 1
    # Increment Alerts with IaC
    if policies[policyId]['policyShiftable']:
        alert_counts['shiftable'] += 1
	# Increment Alerts with Remediation
    if alert['policy']['remediable']:
        alert_counts['remediable'] += 1

##########################################################################################
# Output tables and totals.
##########################################################################################

# Output Compliance Standards with Alerts

print
print('#################################################################################')
print('# SHEET: By Compliance Standard, Open and Closed Alerts, %s' % TIME_RANGE_LABEL)
print('#################################################################################')
print
print('%s\t%s\t%s\t%s' % ('Compliance Standard', 'High-Severity Alert Count', 'Medium-Severity Alert Count', 'Low-Severity Alert Count'))																						
for standard in sorted(alerts_by_compliance_standard):
    print('%s\t%s\t%s\t%s' % (standard, alerts_by_compliance_standard[standard]['high'], alerts_by_compliance_standard[standard]['medium'], alerts_by_compliance_standard[standard]['low']))

# Output Policies with Alerts

print
print('#################################################################################')
print('# SHEET: By Policy, Open and Closed Alerts, %s' % TIME_RANGE_LABEL)
print('#################################################################################')
print
print('%s\t%s\t%s\t%s\t%s\t%s\t%s' % ('policyName', 'policySeverity', 'policyType', 'policyShiftable', 'policyRemediable', 'alertCount', 'policyComplianceStandards') )
for policy in sorted(alerts_by_policy):
    policyId                    = alerts_by_policy[policy]['policyId']
    policyName                  = policies[policyId]['policyName']
    policySeverity              = policies[policyId]['policySeverity']
    policyType                  = policies[policyId]['policyType']
    policyShiftable             = policies[policyId]['policyShiftable']
    policyRemediable            = policies[policyId]['policyRemediable']
    alert_count                 = alerts_by_policy[policy]['alertCount']
    policy_compliance_standards = ','.join(map(str, policies[policyId]['complianceStandards']))
    print('%s\t%s\t%s\t%s\t%s\t%s\t"%s"' % (policyName, policySeverity, policyType, policyShiftable, policyRemediable, alert_count, policy_compliance_standards))

# Output Summary

print
print('#################################################################################')
print('# SHEET: Summary, Open and Closed Alerts, %s' % TIME_RANGE_LABEL)
print('#################################################################################')
print
print("Compliance Standard with Alerts: Total\t%s" % len(alerts_by_compliance_standard))
print
print("Policies with Alerts: Total\t%s"            % len(alerts_by_policy))
print
print("Alerts: Total\t%s"              % len(alert_list))
print("Alerts: Open\t%s"               % alert_counts['open'])
print("Alerts: Resolved\t%s"           % alert_counts['resolved'])
print("Alerts: Resolved by Delete\t%s" % alert_counts['resolved_deleted'])
print("Alerts: Resolved by Update\t%s" % alert_counts['resolved_updated'])
print("Alerts: High-Severity\t%s"      % alert_counts['resolved_high'])
print("Alerts: Medium-Severity\t%s"    % alert_counts['resolved_medium'])
print("Alerts: Low-Severity\t%s"       % alert_counts['resolved_low'])
print("Alerts: Anomaly\t%s"            % policy_counts['anomaly'])
print("Alerts: Config\t%s"             % policy_counts['config'])
print("Alerts: Network\t%s"            % policy_counts['network'])
# Note it appears that `audit_event` alerts are returned from the /policy endpoint, not from the /alert endpoint.
# The `policy_counts` structure counts results from the /alert endpoint. So, included only for reference.
# print("Alerts: Audit\t%s"              % policy_counts['audit_event'])
print("Alerts: with IaC\t%s"           % alert_counts['shiftable'])
print("Alerts: with Remediation\t%s"   % alert_counts['remediable'])
print