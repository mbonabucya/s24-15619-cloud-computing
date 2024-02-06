
import boto3
import botocore
import os
import requests
import time
import json
import configparser
import re
from dateutil.parser import parse
import datetime


########################################
# Constants
########################################
with open('horizontal-scaling-config.json') as file:
    configuration = json.load(file)

LOAD_GENERATOR_AMI = configuration['load_generator_ami']
WEB_SERVICE_AMI = configuration['web_service_ami']
INSTANCE_TYPE = configuration['instance_type']

# Credentials fetched from environment variables
SUBMISSION_USERNAME = os.environ['SUBMISSION_USERNAME']
SUBMISSION_PASSWORD = os.environ['SUBMISSION_PASSWORD']

########################################
# Tags
########################################
tag_pairs = [
    ("Project", "vm-scaling"),
]
TAGS = [{'Key': k, 'Value': v} for k, v in tag_pairs]

TEST_NAME_REGEX = r'name=(.*log)'

########################################
# Utility functions
########################################


def create_instance(ami, sg_id):
    """
    Given AMI, create and return an AWS EC2 instance object
    :param ami: AMI image name to launch the instance with
    :param sg_id: ID of the security group to be attached to instance
    :return: instance object
    """
    # TODO: Create an EC2 instance
    # Wait for the instance to enter the running state
    # Reload the instance attributes

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    waiter = ec2_client.get_waiter('instance_running')

    try:
        response = ec2_client.run_instances(
            ImageId=ami,
            InstanceType =INSTANCE_TYPE,
            KeyName='mykeypair',
            MaxCount=1,
            MinCount=1,
            SecurityGroupIds=[sg_id,],
            TagSpecifications=[{'ResourceType': 'instance', 'Tags': TAGS}]
        )
        instance_id = response['Instances'][0]['InstanceId']
        print(f" the instance with ID: {instance_id} is  created successfully.")
        # wait fore the instance to run 
        waiter.wait(InstanceIds=[instance_id])

        if waiter:
            instance = boto3.resource('ec2').Instance(instance_id)
            instance.load()
            return instance
    
    except Exception as e:
        print(f"Error creating the instance {e}")
        return None
    
    
def initialize_test(lg_dns, first_web_service_dns):
    """
    Start the horizontal scaling test
    :param lg_dns: Load Generator DNS
    :param first_web_service_dns: Web service DNS
    :return: Log file name
    """

    add_ws_string = 'http://{}/test/horizontal?dns={}'.format(
        lg_dns, first_web_service_dns
    )
    response = None
    while not response or response.status_code != 200:
        try:
            response = requests.get(add_ws_string)
            
        except requests.exceptions.ConnectionError:
            print("Error initializing the test")
            time.sleep(1)
        
    # TODO: return log File name
    log = get_test_id(response)
    return log
        
    
def print_section(msg):
    """
    Print a section separator including given message
    :param msg: message
    :return: None
    """
    print(('#' * 40) + '\n# ' + msg + '\n' + ('#' * 40))


def get_test_id(response):
    """
    Extracts the test id from the server response.
    :param response: the server response.
    :return: the test name (log file name).
    """
    response_text = response.text

    regexpr = re.compile(TEST_NAME_REGEX)

    return regexpr.findall(response_text)[0]


def is_test_complete(lg_dns, log_name):
    """
    Check if the horizontal scaling test has finished
    :param lg_dns: load generator DNS
    :param log_name: name of the log file
    :return: True if Horizontal Scaling test is complete and False otherwise.
    """

    log_string = 'http://{}/log?name={}'.format(lg_dns, log_name)

    # creates a log file for submission and monitoring
    f = open(log_name + ".log", "w")
    log_text = requests.get(log_string).text
    f.write(log_text)
    f.close()

    return '[Test finished]' in log_text


def add_web_service_instance(lg_dns, sg2_id, log_name):
    """
    Launch a new WS (Web Server) instance and add to the test
    :param lg_dns: load generator DNS
    :param sg2_id: id of WS security group
    :param log_name: name of the log file
    """
    ins = create_instance(WEB_SERVICE_AMI, sg2_id)
    print("New WS launched. id={}, dns={}".format(
        ins.instance_id,
        ins.public_dns_name)
    )
    add_req = 'http://{}/test/horizontal/add?dns={}'.format(
        lg_dns,
        ins.public_dns_name
    )
    while True:
        if requests.get(add_req).status_code == 200:
            print("New WS submitted to LG.")
            break
        elif is_test_complete(lg_dns, log_name):
            print("New WS not submitted because test already completed.")
            break

def authenticate(lg_dns, submission_password, submission_username):
    """
    Authentication on LG
    :param lg_dns: LG DNS
    :param submission_password: SUBMISSION_PASSWORD
    :param submission_username: SUBMISSION_USERNAME
    :return: None
    """

    authenticate_string = 'http://{}/password?passwd={}&username={}'.format(
        lg_dns, submission_password, submission_username
    )
    response = None
    try:
        response = requests.get(authenticate_string)
        if response.status_code == 200:
            print("Authentication successful.")
        else:
            print(f"Authentication failed. Status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("Connection error occurred. Unable to authenticate.")
  

def get_rps(lg_dns, log_name):
    """
    Return the current RPS as a floating point number
    :param lg_dns: LG DNS
    :param log_name: name of log file
    :return: latest RPS value
    """
    log_string = 'http://{}/log?name={}'.format(lg_dns, log_name)
    config = configparser.ConfigParser(strict=False)
    config.read_string(requests.get(log_string).text)
    sections = config.sections()
    sections.reverse()
    rps = 0
    for sec in sections:
        if 'Current rps=' in sec:
            rps = float(sec[len('Current rps='):])
            break
    return rps


def get_test_start_time(lg_dns, log_name):
    """
    Return the test start time in UTC
    :param lg_dns: LG DNS
    :param log_name: name of log file
    :return: datetime object of the start time in UTC
    """
    log_string = 'http://{}/log?name={}'.format(lg_dns, log_name)
    start_time = None
    while start_time is None:
        config = configparser.ConfigParser(strict=False)
        print(config)
        config.read_string(requests.get(log_string).text)
        # By default, options names in a section are converted
        # to lower case by configparser
        start_time = dict(config.items('Test')).get('starttime', None)
    return parse(start_time)

def create_sg_group(name):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    response = ec2.describe_vpcs()
    vpc = response.get('Vpcs', [{}])[0].get('VpcId', '')
    try:
        response = ec2.create_security_group(GroupName=name,
                                             Description='vm scaling',
                                             VpcId=vpc)
        sgid = response['GroupId']

        ec2.authorize_security_group_ingress(
            GroupId=sgid,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                 'FromPort': 80,
                 'ToPort': 80,
                 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
            ])

        # Adding tags
        ec2.create_tags(
            Resources=[sgid],
            Tags=[
                {'Key': 'Project', 'Value': 'vm-scaling'}
            ]
        )
        print("the security group is created ")
        return sgid

    except Exception as e:
        print(f"Error creating the security group {e}")
    

def terminator(instance_id):
    """
    Terminate an EC2 instance
    :param instance_id: ID of the instance to terminate
    :return: None
    """
    ec2 = boto3.client('ec2',region_name="us-east-1")
    try:
        response = ec2.terminate_instances(InstanceIds=[instance_id])
        print(f"Instance with the ID : {instance_id}  is terminated successfully.")
    except Exception as e:
        print(f"Error terminating instance with ID {instance_id}: {e}")


########################################
# Main routine
########################################
def main():
    # BIG PICTURE TODO: Provision resources to achieve horizontal scalability
    #   - Create security groups for Load Generator and Web Service
    #   - Provision a Load Generator instance
    #   - Provision a Web Service instance
    #   - Register Web Service DNS with Load Generator
    #   - Add Web Service instances to Load Generator
    #   - Terminate resources
    
    print_section('1 - create two security groups')
    sg_permissions = [
        {'IpProtocol': 'tcp',
         'FromPort': 80,
         'ToPort': 80,
         'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
         'Ipv6Ranges': [{'CidrIpv6': '::/0'}],
         }
    ]

    # TODO: Create two separate security groups and obtain the group ids
    sg1_id = create_sg_group(name="LG_SG")  # Security group for Load Generator instances
    sg2_id = create_sg_group(name="WS_SG")  # Security group for Web Service instances

    print_section('2 - create LG')

    # TODO: Create Load Generator instance and obtain ID and DNS
    lg = create_instance(ami=LOAD_GENERATOR_AMI, sg_id=sg1_id)
    if lg is not None:
        lg_id = lg.id
        lg_dns = lg.public_dns_name
    else:
        lg_id = ''
        lg_dns = ''

    print("Load Generator running: id={} dns={}".format(lg_id, lg_dns))
    time.sleep(20)
    print("=======  Creating the web server ====")
    web = create_instance(ami=WEB_SERVICE_AMI, sg_id=sg2_id)
    if web is not None:
        web_id = web.id
        web_service_dns = web.public_dns_name
    else:
        web_id = ''
        web_service_dns = ''
    print(f"web service with id {web_id} is created with dns {web_service_dns}")
    time.sleep(20)
    print_section('3. Authenticate with the load generator')
    authenticate(lg_dns, SUBMISSION_PASSWORD, SUBMISSION_USERNAME)

    # TODO: Create First Web Service Instance and obtain the DNS
    
    # web = create_instance(ami=WEB_SERVICE_AMI, sg_id=sg2_id)
    # web_service_dns = web.public_dns_name

    print_section('4. Submit the first WS instance DNS to LG, starting test.')
    log_name = initialize_test(lg_dns, web_service_dns)
    last_launch_time = get_test_start_time(lg_dns, log_name)
    last_launch_time_seconds = last_launch_time.timestamp()

    while not is_test_complete(lg_dns, log_name):
        time.sleep(1)
        rps = get_rps(lg_dns=lg_dns,log_name=log_name)
        current_time_seconds = time.time()
        time_diff = current_time_seconds - last_launch_time_seconds
        if rps < 50.0 and time_diff > 100:
            add_web_service_instance(lg_dns=lg_dns,sg2_id=sg2_id,log_name=log_name)
            last_launch_time_seconds =current_time_seconds

        # update = time.time()
        # last_launch_time_seconds =update
        

        # TODO: Check RPS and last launch time
        # TODO: Add New Web Service Instance if Required
    print_section('End Test')


if __name__ == '__main__':
    main()
