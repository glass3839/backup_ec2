""" BACKUP EC2 """
# encoding:utf-8
from datetime import datetime
import boto3
from botocore.client import ClientError
from pytz import timezone

AWS_REGION = ''
TAG_KEY = 'BackupGeneration'
AMI_DESCRIPTION = 'AutoBackup'
AMI_NOREBOOT = True

EC2 = boto3.client('ec2', region_name=AWS_REGION)
EC2_RESOURCE = boto3.resource('ec2', region_name=AWS_REGION)

def lambda_handler(event, context):
    target = def_get_backup_target()
    amis = def_create_backup(target)
    def_set_ami_tag(amis)
    def_remove_backup(amis)
    def_set_snapshot_tag(amis)

def def_get_backup_target():
    """
    OverView:   get ec2instance where BackupGeneration grater than 0
    Return:     [{Tags, InstanceId}]
    """
    backup_target = []
    response = EC2.describe_instances(Filters=[{
        'Name': 'tag-key',
        'Values': [TAG_KEY]
    }])['Reservations']
    for reservation in response:
        for i in reservation['Instances']:
            instance = {t['Key']: t['Value'] for t in i['Tags']}
            instance['InstanceId'] = i['InstanceId']
            try:
                instance[TAG_KEY] = int(instance[TAG_KEY])
            except:
                instance[TAG_KEY] = 0  # for BackupGeneration is not int
                print 'err invalid ' + TAG_KEY + ':' + instance['Name']
            finally:
                if instance[TAG_KEY] >= 0:
                    backup_target.append(instance)
        return backup_target

def def_create_backup(backup_targets):
    """
    OverView:   create ami
    Parameter:  backup_targets [list{dict}]
    Return:     [{Tags, InstanceId, ImageId}]
    """
    if backup_targets is None:
        raise Exception('no backup target')
    ami_list = []
    for target in backup_targets:
        jst_now = datetime.now(timezone('UTC')).astimezone(
            timezone('Asia/Tokyo')).strftime('%Y%m%d%H%M%S')
        try:
            response = EC2.create_image(
                InstanceId=target['InstanceId'],
                Name=target['Name'] + '_' + jst_now,
                Description=AMI_DESCRIPTION,
                NoReboot=AMI_NOREBOOT
            )['ImageId']
        except ClientError as ex:
            print 'err fail create image ' + ':' + target['Name']
            print str(ex)
        else:
            target['ImageId'] = response
            ami_list.append(target)
            print 'info creating image ' + ':' + target['Name']
    return ami_list

def def_set_ami_tag(ami_list):
    """
    OverView:   set tag:name for ami
    Parameter:  ami_list [list{dict}]
    Return:     null
    """
    for ami in ami_list:
        EC2.get_waiter('image_available').wait(
            ImageIds=[ami['ImageId']]
        )
        try:
            def_set_tag(ami['ImageId'], ami['Name'])
        except ClientError as ex:
            print str(ex)

def def_set_snapshot_tag(ami_list):
    """
    OverView:   set tag:name for snapshot
    Parameter:  ami_list [list{dict}
    Return:     null
    """
    for ami in ami_list:
        response = EC2_RESOURCE.Image(ami['ImageId'])
        for bdm in response.block_device_mappings:
            def_set_tag(bdm['Ebs']['SnapshotId'], ami['Name'])

def def_remove_backup(backup_targets):
    """
    OverView:   delete image & snapshot
    Parameter:  backup_targets [list{dict}]
    Return:     null
    """
    for target in backup_targets:
        for i, image in enumerate(def_get_image(target['Name'])):
            if target[TAG_KEY] < i + 1:
                response = EC2_RESOURCE.Image(image['ImageId'])
                try:
                    print 'info deregist ami : ' + image['Name']
                    block_device_mappings = response.block_device_mappings
                    response.deregister()
                except ClientError as ex:
                    print 'err deregist ami : ' + image['Name'] + ' ' + str(ex)
                for bdm in block_device_mappings:
                    try:
                        print 'info delete snapshot : ' + bdm['Ebs']['SnapshotId']
                        EC2_RESOURCE.Snapshot(bdm['Ebs']['SnapshotId']).delete()
                    except ClientError as ex:
                        print 'err delete snapshot : ' + bdm['Ebs']['SnapshotId'] + ' ' + str(ex)

def def_get_image(tag_name):
    """
    OverView:   get image info
    Parameter:  tag Name
    Return:     image info [list]
    """
    try:
        response = EC2.describe_images(Filters=[{
            'Name': 'tag-key',
            'Values':   ['Name']
        }, {
            'Name': 'tag-value',
            'Values': [tag_name]
        }])['Images']
    except ClientError as ex:
        print 'err error get image info ' + tag_name + ':' + str(ex)
    image_list = sorted(
        response, key=lambda x: x['CreationDate'], reverse=True
    )
    return image_list

def def_set_tag(resource_id, key_value):
    """ create tag:name """
    try:
        EC2.create_tags(
            Resources=[resource_id],
            Tags=[{
                'Key': 'Name',
                'Value': key_value
            }])
    except ClientError as ex:
        print str(ex)
