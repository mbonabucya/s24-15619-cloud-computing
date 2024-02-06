
import boto3
import botocore
import os
import requests
import time
import json
import re

########################################
# Constants
########################################
with open('auto-scaling-config.json') as file:
    configuration = json.load(file)

LOAD_GENERATOR_AMI = configuration['load_generator_ami']
WEB_SERVICE_AMI = configuration['web_service_ami']
INSTANCE_TYPE = configuration['instance_type']
LAUNCH_TEMPLATE_NAME= configuration['launch_template_name']
AUTO_SCALING_GROUP_NAME = configuration['auto_scaling_group_name']
AUTO_SCALING_GROUP_MAX_SIZE = configuration['asg_max_size']
AUTO_SCALING_GROUP_MIN_SIZE = configuration['asg_min_size']
AUTO_SCALING_TARGET_GROUP_NAME = configuration['auto_scaling_target_group']
LOAD_BALANCER_NAME = configuration['load_balancer_name']
SCALE_IN_ADJUSTMENT = configuration['scale_in_adjustment']
COOL_DOWN_SCALE_IN = configuration['cool_down_period_scale_in']
DEFAULT_COOL_DOWN = configuration['asg_default_cool_down_period']
SCALE_OUT_ADJUSTMENT = configuration['scale_out_adjustment']
COOL_DOWN_SCALE_OUT = configuration['cool_down_period_scale_out']
ADJUSTMENT_TYPE = configuration['adjustment_type']
CPU_UPPER_THRESHOLD = configuration['cpu_upper_threshold']
CPU_LOWER_THRESHOLD = configuration['cpu_lower_threshold']
SCALE_IN_EVALUATION= configuration['alarm_evaluation_periods_scale_in']
SCALE_OUT_EVALUATION = configuration['alarm_evaluation_periods_scale_out']
ALARM_PERIOD = configuration['alarm_period']
GRACE_PERIOD = configuration['health_check_grace_period']
DESIRED_CAPACITY =configuration['desired_capacity']
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
    instance = None

    # TODO: Create an EC2 instance
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





def initialize_test(load_generator_dns, first_web_service_dns):
    """
    Start the auto scaling test
    :param lg_dns: Load Generator DNS
    :param first_web_service_dns: Web service DNS
    :return: Log file name
    """

    add_ws_string = 'http://{}/autoscaling?dns={}'.format(
        load_generator_dns, first_web_service_dns
    )
    response = None
    while not response or response.status_code != 200:
        try:
            response = requests.get(add_ws_string)
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            pass 

    # TODO: return log File name
    return get_test_id(response=response)


def initialize_warmup(load_generator_dns, load_balancer_dns):
    """
    Start the warmup test
    :param lg_dns: Load Generator DNS
    :param load_balancer_dns: Load Balancer DNS
    :return: Log file name
    """

    add_ws_string = 'http://{}/warmup?dns={}'.format(
        load_generator_dns, load_balancer_dns
    )
    response = None
    while not response or response.status_code != 200:
        try:
            response = requests.get(add_ws_string)
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            pass  

    # TODO: return log File name
    return get_test_id(response=response)


def get_test_id(response):
    """
    Extracts the test id from the server response.
    :param response: the server response.
    :return: the test name (log file name).
    """
    response_text = response.text

    regexpr = re.compile(TEST_NAME_REGEX)

    return regexpr.findall(response_text)[0]


def destroy_resources(msg,target_arn,temp_id,load_arn,sgid,lg_id):
    """
    Delete all resources created for this task

    You must destroy the following resources:
    Load Generator, Auto Scaling Group, Launch Template, Load Balancer, Security Group.
    Note that one resource may depend on another, and if resource A depends on resource B, you must delete resource B before you can delete resource A.
    Below are all the resource dependencies that you need to consider in order to decide the correct ordering of resource deletion.

    - You cannot delete Launch Template before deleting the Auto Scaling Group
    - You cannot delete a Security group before deleting the Load Generator and the Auto Scaling Groups
    - You must wait for the instances in your target group to be terminated before deleting the security groups

    :param msg: message
    :param target_arn: target group ARN
    :param lg_id : id of the loadgenerator 
    :param temp_id : launch template id
    :param load_arn : Loadbalancer ARN
    :param sgid : security group ID
    :return: None
    """
    # TODO: implement this method
    if msg.lower() =='yes':
        print("we will be destroying all the resources .....")
        # initialize the boto clients
        ec2_client = boto3.client("ec2", region_name="us-east-1")
        client_asg = boto3.client('autoscaling',region_name="us-east-1")
        client_lb = boto3.client('elbv2',region_name="us-east-1")
        ec2 = boto3.resource('ec2')
        
        try:

            # 1 delete the LG
            print_section("1. Deleting the LG .....")
            instance =ec2.Instance(lg_id)
            ec2_client.terminate_instances( 
            InstanceIds=[lg_id,
            ],)
            print("wait while loadgenerator is terminating")
            instance.wait_until_terminated()

            print_section("2. deleting the autoscaling group ......")
            response = client_asg.describe_auto_scaling_groups(AutoScalingGroupNames=[AUTO_SCALING_GROUP_NAME])
            asg_name = response['AutoScalingGroups'][0]['AutoScalingGroupName']
            client_asg.delete_auto_scaling_group(
            AutoScalingGroupName=asg_name,
            ForceDelete=True)
            time.sleep(240)


            # delete launch template 
            print_section("3. delete the launch template ....")
            ec2_client.delete_launch_template(LaunchTemplateId=temp_id,)
            

            # load balancer 
            print_section("4. delete the loadbalancer")
            client_lb.delete_load_balancer(LoadBalancerArn=load_arn)
            time.sleep(120)
    
            # target group 
            print_section("5. delete the target group")
            client_lb.delete_target_group(TargetGroupArn=target_arn)

            print_section("6. delete the security groups .....")
            for group_id in sgid:
                ec2_client.delete_security_group(GroupId=group_id,)
                print(f"Security Group with ID {group_id} deleted.")
            print("All resources have been terminated.")

        except Exception as e:
            print(f"Error: {str(e)}")
    
    else:
        print("the resources are not terminated , you might incur additional charges")

def print_section(msg):
    """
    Print a section separator including given message
    :param msg: message
    :return: None
    """
    print(('#' * 40) + '\n# ' + msg + '\n' + ('#' * 40))


def is_test_complete(load_generator_dns, log_name):
    """
    Check if auto scaling test is complete
    :param load_generator_dns: lg dns
    :param log_name: log file name
    :return: True if Auto Scaling test is complete and False otherwise.
    """
    log_string = 'http://{}/log?name={}'.format(load_generator_dns, log_name)

    # creates a log file for submission and monitoring
    f = open(log_name + ".log", "w")
    log_text = requests.get(log_string).text
    f.write(log_text)
    f.close()

    return '[Test finished]' in log_text


def authenticate(load_generator_dns, submission_password, submission_username):
    """
    Authentication on LG
    :param load_generator_dns: LG DNS
    :param submission_password: SUBMISSION_PASSWORD
    :param submission_username: SUBMISSION_USERNAME
    :return: None
    """
    authenticate_string = 'http://{}/password?passwd={}&username={}'.format(
        load_generator_dns, submission_password, submission_username
    )
    response = None
    while not response or response.status_code != 200:
        try:
            response = requests.get(authenticate_string)
            print("authentication is susccessfull")
            break
        except requests.exceptions.ConnectionError:
            pass


# create the security groups function 

def create_sg_group(name):
    """
    Create the security group
    :param name of the security group
    :return: security group ID 
    """
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


## create the launch template 
        
def create_lt(sg):
    """
    launch template function with the necessary data
    :param security group id for ASG and ELB
    :return: Launch template ID
    """
    ec2_client = boto3.client('ec2',region_name="us-east-1")
    response =None
    try:
        response = ec2_client.create_launch_template(
            LaunchTemplateName=LAUNCH_TEMPLATE_NAME,
            VersionDescription='initial version',
            LaunchTemplateData={
            'ImageId': WEB_SERVICE_AMI,  # Web service AMI ID
            'InstanceType': 'm5.large',
            'Monitoring': {
                'Enabled': True
            },
            'SecurityGroupIds': [
                sg
            ],
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Project',
                            'Value': 'vm-scaling'
                        }
                    ]
                }
            ]

            },
        )
        launch_template_id = response['LaunchTemplate']['LaunchTemplateId']
        print(f"Launch template created with ID : {launch_template_id}")
        return launch_template_id

    except Exception as e:
        print(f"Error creating the Launch template with exception: {e}")
    

# create the target group 
def create_target_group(target_name):
    """
    create the target group
    :param name of the target group
    :return: target group ARN
    """
    client = boto3.client('elbv2',region_name="us-east-1")
    vpc_object = boto3.client('ec2',region_name="us-east-1")
    vpcs = vpc_object.describe_vpcs()
    vpcid = vpcs.get('Vpcs', [{}])[0].get('VpcId', '')
    try:
        response = client.create_target_group(
        Name=target_name,
        Protocol='HTTP',
        Port=80,
        VpcId=vpcid,
        HealthCheckProtocol='HTTP',
        HealthCheckPort='traffic-port',
        HealthCheckEnabled=True,
        HealthCheckPath='/',
        HealthCheckIntervalSeconds=123,
        HealthCheckTimeoutSeconds=60,
        HealthyThresholdCount=10,
        UnhealthyThresholdCount=10,
        TargetType='instance',
        Tags=[
            {
                'Key': 'Project',
                'Value': 'vm-scaling'
            },
        ],
        )
        target_arn = response['TargetGroups'][0]['TargetGroupArn']
        print(f"The target ARN : ===>{target_arn}")

        return target_arn
    except Exception as e:
        print(f" error occured creating the target group: {e}")

# create a LB 

def create_load_balancer(lb_name,sg):
    """
    create the LoadBalancer
    :param name of the Load Balancer
    :return: Load Balance object
    """
    subnets_object = boto3.client('ec2', region_name="us-east-1")
    vpcs = subnets_object.describe_vpcs()
    vpcid = vpcs.get('Vpcs', [{}])[0].get('VpcId', '')
    response = subnets_object.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpcid]}])
    subnet_ids = [subnet['SubnetId'] for subnet in response['Subnets']]

    client = boto3.client('elbv2',region_name="us-east-1")
    try:
        response = client.create_load_balancer(
        Name=lb_name,
        Subnets=subnet_ids,
        SecurityGroups=[
            sg,
        ],
        Tags=[
            {
                'Key': 'Project',
                'Value': 'vm-scaling'
            },
        ],
        Type='application',
        
    )
        waiter = client.get_waiter('load_balancer_available')
        if waiter:
            waiter.wait(LoadBalancerArns=[response['LoadBalancers'][0]['LoadBalancerArn']])
            lb_describe_response = client.describe_load_balancers(LoadBalancerArns=[response['LoadBalancers'][0]['LoadBalancerArn']])
            lb_state = lb_describe_response['LoadBalancers'][0]['State']['Code']
            print(f"Load Balancer state: {lb_state}")
            print("Load Balancer created successfully.")
            return response
            
    except Exception as e:
        print(f"error creating the LB {e}")



def associate_lb_target_group(lb_arn,target_arn):
    """
    create the LoadBalancer listener
    :param loadbalancer ARN
    :param target group arn
    :return: Load Balance object
    """
    elb_client = boto3.client('elbv2', region_name="us-east-1")

    if lb_arn is not None and target_arn is not None:
        response = elb_client.create_listener(
            LoadBalancerArn=lb_arn,
            Protocol='HTTP',
            Port=80,
            DefaultActions=[
            {
                'Type':'forward',
                'TargetGroupArn': target_arn,
    
            },
            ],
            Tags=[
            {
                'Key': 'Project',
                'Value': 'vm-scaling'
            },
        ]
        )
        print("The LB is listening at port 80")
        print(f" passed target_arn {target_arn} and lb_arn {lb_arn}")
      
    else:
        print("Association failed ===> There might be not Lb_arn or target_arn")



# create the autoscaling group 
        
def create_asg(launch_template_id, target_group_arn):
    """
    create the autoscaling groupe
    :param launch template id
    :param target group arn
    :return: autoscaling group name
    """
    client = boto3.client('autoscaling',region_name="us-east-1")
    try:
        response = client.create_auto_scaling_group(
            AutoScalingGroupName=AUTO_SCALING_GROUP_NAME,
            MinSize=AUTO_SCALING_GROUP_MIN_SIZE,
            MaxSize=AUTO_SCALING_GROUP_MAX_SIZE,
            DesiredCapacity=DESIRED_CAPACITY,
            DefaultCooldown=DEFAULT_COOL_DOWN,
            HealthCheckGracePeriod=GRACE_PERIOD,
            HealthCheckType='EC2',
            AvailabilityZones=['us-east-1a'],
            LaunchTemplate={
                'LaunchTemplateId': launch_template_id,
                'Version': '$Latest'
            },
            TargetGroupARNs=[target_group_arn],
            Tags=[
                {
                    'Key': 'Project',
                    'Value': 'vm-scaling',
                    'PropagateAtLaunch': True
                }
            ]
        )

        response = client.describe_auto_scaling_groups(AutoScalingGroupNames=[AUTO_SCALING_GROUP_NAME])
        asg_name = response['AutoScalingGroups'][0]['AutoScalingGroupName']
        print(f"auto scaling group name {asg_name}")
        return asg_name

    except Exception as e :
        print(f"Error occured: {e}")


def scaling_policy(asg_name, policy_name, scaling_adjustment, adjustment_type, cooldown):
    """
    Create Auto Scaling policy (scale_in or scale_out).
    :param autoscaling_group_name: Name of the associated Auto Scaling Group.
    :param policy_name: Name of the scaling policy.Name will be required to take the alarm actions
    :param scaling_adjustment: The number of instances by which to scale.
    :param adjustment_type: Type of adjustment
    :param cooldown: The amount of time, in seconds, after a previous scaling activity completes.
    :return: Scaling policy arn.
    """
    client = boto3.client('autoscaling', region_name="us-east-1")
    try:
        response = client.put_scaling_policy(
            AutoScalingGroupName=asg_name,
            PolicyName=policy_name,
            PolicyType='SimpleScaling',
            ScalingAdjustment=scaling_adjustment,
            AdjustmentType=adjustment_type,
            Cooldown=cooldown
        )
        policy_arn = response['PolicyARN']
        return policy_arn
    except Exception as e :
        print(f"Error {e}")


def create_alarm(alarm_name, comparison_operator, alarm_description, alarm_actions,cpu_threshold,asg_name):
    """
    Create alarm.
    :param autoscaling_group_name: Name of the associated Auto Scaling Group.
    :param alarm_name: the alarm actions
    :param comparison_operator: comparison to the threshold.
    :param alarm_description: describe the alarm 
    :param cpu_threshold: threshold  
    :param alarm_actions: action to associate with the autoscaling policies
    :return: None.
    """

    client = boto3.client('cloudwatch',region_name="us-east-1")
    try:
        response = client.put_metric_alarm(
    AlarmName=alarm_name,
    AlarmDescription=alarm_description,
    EvaluationPeriods=2,
    ActionsEnabled=True,
    AlarmActions=[
        alarm_actions,
    ],
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Statistic='Average',
    Dimensions=[
        {
        'Name': 'AutoScalingGroupName',
        'Value': asg_name
        },
    ],
    Period=ALARM_PERIOD,
    Unit='Seconds',
    Threshold=cpu_threshold,
    ComparisonOperator=comparison_operator,
    Tags=[
        {
            'Key': 'Project',
            'Value': 'vm-scaling'
        },
    ],
)
        return response
    except Exception as e:
        print(f"{e}")
   


########################################
# Main routine
########################################
def main():
    # BIG PICTURE TODO: Programmatically provision autoscaling resources
    #   - Create security groups for Load Generator and ASG, ELB
    #   - Provision a Load Generator
    #   - Generate a Launch Template
    #   - Create a Target Group
    #   - Provision a Load Balancer
    #   - Associate Target Group with Load Balancer
    #   - Create an Autoscaling Group
    #   - Initialize Warmup Test
    #   - Initialize Autoscaling Test
    #   - Terminate Resources

    print_section('1 - create two security groups')

    PERMISSIONS = [
        {'IpProtocol': 'tcp',
         'FromPort': 80,
         'ToPort': 80,
         'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
         'Ipv6Ranges': [{'CidrIpv6': '::/0'}],
         }
    ]

    # TODO: create two separate security groups and obtain the group ids
    sg1_id = create_sg_group(name="Loadgenerator_sg")  # Security group for Load Generator instances
    sg2_id = create_sg_group(name="elb_asg") # Security group for ASG, ELB instances

    print_section('2 - create LG')

    # TODO: Create Load Generator instance and obtain ID and DNS
    lg = create_instance(ami=LOAD_GENERATOR_AMI,sg_id=sg1_id)
    if lg is not None:
        lg_id = lg.id
        lg_dns = lg.public_dns_name
    else:
        lg_id = ''
        lg_dns = ''

    print("Load Generator running: id={} dns={}".format(lg_id, lg_dns))

    print_section('3. Create LT (Launch Template)')
    # TODO: create launch Template
    lt_id = create_lt(sg=sg2_id)

    print_section('4. Create TG (Target Group)')
    # TODO: create Target Group
    tg_arn = create_target_group(target_name=AUTO_SCALING_TARGET_GROUP_NAME)

    print_section('5. Create ELB (Elastic/Application Load Balancer)')
    # TODO create Load Balancer

    lb = create_load_balancer(lb_name=LOAD_BALANCER_NAME,sg=sg2_id)
    lb_arn = lb['LoadBalancers'][0]['LoadBalancerArn']
    lb_dns = lb['LoadBalancers'][0]['DNSName']
    print("lb started. ARN={}, DNS={}".format(lb_arn, lb_dns))

    print_section('6. Associate ELB with target group')
    # TODO Associate ELB with target group
    associate_lb_target_group(lb_arn=lb_arn,target_arn=tg_arn)
    # register_target(instace_id=lg_id,target_arn=tg_arn)

    print_section('7. Create ASG (Auto Scaling Group)')
    # TODO create Autoscaling group
    asgname = create_asg(launch_template_id=lt_id,target_group_arn=tg_arn)

    print_section('8. Create policy and attached to ASG')
    # TODO Create Simple Scaling Policies for ASG
    scaling_in_arn = scaling_policy(asg_name=asgname,policy_name='scale-in-policy',scaling_adjustment=SCALE_IN_ADJUSTMENT,adjustment_type=ADJUSTMENT_TYPE,cooldown=COOL_DOWN_SCALE_IN)
    scaling_out_arn = scaling_policy(asg_name=asgname,policy_name='scale_out_policy',scaling_adjustment=SCALE_OUT_ADJUSTMENT,adjustment_type=ADJUSTMENT_TYPE,cooldown=COOL_DOWN_SCALE_OUT)
    print(f"Scaling In ARN {scaling_in_arn} and scale out ARN {scaling_out_arn}")

    print_section('9. Create Cloud Watch alarm. Action is to invoke policy.')
    # TODO create CloudWatch Alarms and link Alarms to scaling policies
    create_alarm(alarm_name='scaling_in_arm', comparison_operator='GreaterThanThreshold', alarm_description='Alarm when CPU exceeds 80%', alarm_actions=scaling_out_arn,cpu_threshold=CPU_UPPER_THRESHOLD,asg_name=asgname)
    create_alarm(alarm_name='scaling_in_arm', comparison_operator='LessThanThreshold', alarm_description='Alarm when CPU is less than 20%', alarm_actions=scaling_in_arn,cpu_threshold=CPU_LOWER_THRESHOLD,asg_name=asgname)

    print_section('10. Authenticate with the load generator')
    authenticate(lg_dns, SUBMISSION_PASSWORD, SUBMISSION_USERNAME)

    print_section('11. Submit ELB DNS to LG, starting warm up test.')
    warmup_log_name = initialize_warmup(lg_dns, lb_dns)
    while not is_test_complete(lg_dns, warmup_log_name):
        time.sleep(1)

    print_section('12. Submit ELB DNS to LG, starting auto scaling test.')
    # May take a few minutes to start actual test after warm up test finishes
    log_name = initialize_test(lg_dns, lb_dns)
    while not is_test_complete(lg_dns, log_name):
        time.sleep(1)

    print("13. Are you sure you want to terminate all resources??")
    message = input("TYPE YES to confirm \n")
    security_group_ids =[sg1_id,sg2_id]
    destroy_resources(msg=message,load_arn=lb_arn,lg_id=lg_id,sgid=security_group_ids,target_arn=tg_arn,temp_id=lt_id)


if __name__ == "__main__":
    main()
