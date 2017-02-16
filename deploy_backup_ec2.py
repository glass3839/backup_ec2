# encoding:utf-8
import json
import zipfile
import os
import boto3
from botocore.client import ClientError

### parameter ###
# aws account & region name
AWS_ACCOUNT = ''
AWS_REGION = ''

# backup schedule
SCHEDULE_NAME = 'Backup_EC2'
SCHEDULE_DESCRIPTION = 'Backup_EC2'
SCHEDULE = 'cron(0 17 * * ? *)'
SCHEDULE_STATE = 'ENABLED'

# code file name & external libraries
CODE_FILE_NAME = 'backup_ec2.py'
LIB_NAME = ['pytz']  # external library name

# lambda function configuration
LAMBDA_FUNCTION_NAME = 'Backup_EC2'
LAMBDA_ROLE_NAME = 'lmd_' + LAMBDA_FUNCTION_NAME
LAMBDA_RUNTIME = 'python2.7'
LAMBDA_HANDLER = CODE_FILE_NAME.split('.')[0]
LAMBDA_DESCRIPTION = 'BACKUP_EC2'
LAMBDA_TIMEOUT = 180
LAMBDA_MEMORY_SIZE = 128
LAMBDA_PUBLISH = False
LAMBDA_SUBNET_ID = []
LAMBDA_SECURITYGROUP = []

# alert action
ALARM_NAME = 'ALARM_Backup_EC2'
ALARM_PROTOCOL = 'email'
ALARM_ITEM = []

# iam role policies
IAM_ROLE_ASSUME_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"}]})
IAM_ROLE_PERMISSION = json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "logs:DescribeLogStreams"
        ],
        "Resource":[
            "arn:aws:logs:*:*:*"
        ]
    }, {
        "Effect": "Allow",
        "Action": [
            "ec2:CreateNetworkInterface",
            "ec2:DeleteNetworkInterface",
            "ec2:Describe*",
            "ec2:CreateImage",
            "ec2:DeregisterImage",
            "ec2:CreateSnapshot",
            "ec2:DeleteSnapshot",
            "ec2:CreateTags"
        ],
        "Resource": "*"}]})

### functions ###


def def_create_iam_role_lambda():
    """
    OverView:   create iam role for lambda function
    Return:     null
    """
    iam = boto3.client('iam', region_name=AWS_REGION)
    print 'creating iam role : ' + LAMBDA_ROLE_NAME
    try:
        iam.create_role(
            Path='/service-role/',
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=IAM_ROLE_ASSUME_POLICY)
    except ClientError as ex:
        print ' ' + str(ex)
    else:
        print 'created iam role'
    iam_resource = boto3.resource('iam', region_name=AWS_REGION).RolePolicy(
        LAMBDA_ROLE_NAME, LAMBDA_ROLE_NAME)
    try:
        print 'updating inline policy : ' + LAMBDA_ROLE_NAME
        iam_resource.put(
            PolicyDocument=IAM_ROLE_PERMISSION)
    except ClientError as ex:
        print ' ' + str(ex)
    else:
        print 'updated inline policy'


def def_get_lambda_function():
    """
    OverView:   get lambda arn
    Return:     lambda_arn(string)
    """
    lmd = boto3.client('lambda', region_name=AWS_REGION)
    try:
        response = lmd.get_function(
            FunctionName=LAMBDA_FUNCTION_NAME
        )['Configuration']['FunctionArn']
        return response
    except ClientError as ex:
        return ''


def def_create_lambda_function():
    """
    OverView:   create lambda function
    Return:     lambda_arn(string)
    """
    lmd = boto3.client('lambda', region_name=AWS_REGION)
    content = def_upload_file()
    try:
        print 'creating lambda function : ' + LAMBDA_FUNCTION_NAME
        response = lmd.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime=LAMBDA_RUNTIME,
            Role='arn:aws:iam::' + AWS_ACCOUNT + ':role/service-role/' + LAMBDA_ROLE_NAME,
            Handler=CODE_FILE_NAME.split('.')[0] + '.lambda_handler',
            Code={'ZipFile': content},
            Description=LAMBDA_DESCRIPTION,
            Timeout=LAMBDA_TIMEOUT,
            MemorySize=LAMBDA_MEMORY_SIZE,
            Publish=LAMBDA_PUBLISH,
            VpcConfig={'SubnetIds': LAMBDA_SUBNET_ID,
                       'SecurityGroupIds': LAMBDA_SECURITYGROUP}
        )['FunctionArn']
    except ClientError as ex:
        print ' ' + str(ex)
    else:
        print 'created lambda function'
        return response


def def_update_lambda_function():
    """
    OverView:   update lambda code and configuration
    Return:     null
    """
    lmd = boto3.client('lambda', region_name=AWS_REGION)
    content = def_upload_file()
    try:
        print 'updating lambda function: ' + LAMBDA_FUNCTION_NAME
        lmd.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=content,
            Publish=LAMBDA_PUBLISH
        )
        lmd.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Role='arn:aws:iam::' + AWS_ACCOUNT + ':role/service-role/' + LAMBDA_ROLE_NAME,
            Handler=CODE_FILE_NAME.split('.')[0] + '.lambda_handler',
            Description=LAMBDA_DESCRIPTION,
            Timeout=LAMBDA_TIMEOUT,
            VpcConfig={'SubnetIds': LAMBDA_SUBNET_ID,
                       'SecurityGroupIds': LAMBDA_SECURITYGROUP}
        )
    except ClientError as ex:
        print ' ' + str(ex)
    else:
        print 'updated lambda function'


def def_put_schedule():
    """
    OverView:   put backup schedule
    Return:     null
    """
    cwe = boto3.client('events', region_name=AWS_REGION)
    try:
        print 'put backup schedule for ' + SCHEDULE_NAME
        cwe.put_rule(
            Name=SCHEDULE_NAME,
            ScheduleExpression=SCHEDULE,
            State=SCHEDULE_STATE,
            Description=SCHEDULE_DESCRIPTION
        )
        cwe.put_targets(
            Rule=SCHEDULE_NAME,
            Targets=[
                {'Id': LAMBDA_FUNCTION_NAME, 'Arn': LMD_ARN}
            ]
        )
    except ClientError as ex:
        print ' ' + str(ex)
    else:
        print 'put backup schedule'


def def_create_snstopic():
    """
    OverView:   alarm setting
    Return:     null
    """
    sns = boto3.client('sns', region_name=AWS_REGION)
    topics = sns.list_topics()['Topics']
    for topic in topics:
        if ALARM_NAME in topic['TopicArn']:
            sns_arn = topic['TopicArn']
            return sns_arn
        else:
            try:
                print 'creating sns topic : ' + ALARM_NAME
                sns_arn = sns.create_topic(Name=ALARM_NAME)['TopicArn']
            except ClientError as ex:
                print ' ' + str(ex)
            else:
                print 'created sns topic'
                return sns_arn


def def_create_sns_subscription():
    """
    OverView:   create sns subscription
    Return:     null
    """
    sns = boto3.client('sns', region_name=AWS_REGION)
    subscriptions = sns.list_subscriptions_by_topic(
        TopicArn=SNS_ARN
    )['Subscriptions']
    if len(subscriptions) != 0:
        for subscript in subscriptions:
            ALARM_ITEM.remove(subscript['Endpoint'])
    for item in ALARM_ITEM:
        try:
            print 'creating sns subscribe : ' + item
            sns.subscribe(
                TopicArn=SNS_ARN,
                Protocol=ALARM_PROTOCOL,
                Endpoint=item
            )
        except ClientError as ex:
            print ' ' + str(ex)
        else:
            print 'created sns subscribe'


def def_put_cloudwatch_alarm():
    """
    OverView:   put cloudwatch alarm
    Return:     null
    """
    cwa = boto3.client('cloudwatch', region_name=AWS_REGION)
    try:
        print 'put cloudwatch alarm : ' + ALARM_NAME
        cwa.put_metric_alarm(
            AlarmName=ALARM_NAME,
            AlarmDescription=ALARM_NAME,
            ActionsEnabled=True,
            AlarmActions=[SNS_ARN],
            MetricName='Errors',
            Namespace='AWS/Lambda',
            Statistic='Sum',
            Dimensions=[{'Name': 'FunctionName',
                         'Value': LAMBDA_FUNCTION_NAME}],
            Period=300,
            EvaluationPeriods=1,
            Threshold=1,
            ComparisonOperator='GreaterThanOrEqualToThreshold'
        )
    except ClientError as ex:
        print ' ' + str(ex)
    else:
        print 'put cloudwatch alarm'


def def_upload_file():
    """
    OverView:   compress code and library files
    Return:     zip_file.read()
    """
    workdir = os.path.dirname(__file__)
    zipfile_name = CODE_FILE_NAME.split('.')[0] + '.zip'
    with zipfile.ZipFile(os.path.join(workdir, zipfile_name), 'w') as zip_file:
        zip_file.write(CODE_FILE_NAME)
        for lib in LIB_NAME:
            for root, dirs, files in os.walk(lib):
                for _file in files:
                    filename = os.path.join(root, _file)
                    zip_file.write(filename)
        zip_file.close()
    with open(zipfile_name, 'r') as zip_file:
        content = zip_file.read()
    return content

### main ###
def_create_iam_role_lambda()  # Create IAM Role
LMD_ARN = def_get_lambda_function()
if LMD_ARN == '':
    LMD_ARN = def_create_lambda_function()  # Create Lambda Function
else:
    def_update_lambda_function()  # Put Lamdafunction, Code & Configuration
def_put_schedule()  # Put Backup Schedule
SNS_ARN = def_create_snstopic()
def_create_sns_subscription()
def_put_cloudwatch_alarm()
