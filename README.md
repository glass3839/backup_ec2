# Backup EC2 Instance
指定された世代数、EC2のバックアップをおこなう.

バックアップ対象：EC2 Tag-Name:BackupGeneration が設定されているもの.
BackupGenerationは0以上のint型

Error handling：CloudWatchAlarmでError検知.SNS経由でMailする.

## 構成イメージ
![image](https://raw.githubusercontent.com/glass3839/image/master/backup_ec2_design.png)

## Install
```bash
$ git clone git@github.com:glass3839/backup_ec2.git
$ pip install pytz -t ./backup_ec2
$ cd backup_ec2/
$ vi deploy_backup_ec2.py
  ### parameter ###
  AWS_ACCOUNT = 'AWSアカウント名'
  AWS_REGION = 'region名'
  SCHEDULE = 'バックアップ時間'
  LAMBDA_SUBNET_ID = ['subnetid','subnetid']
  LAMBDA_SECURITYGROUP = ['securitygroupid']
  ALARM_ITEM = ['mailaddress']
$ vi backup_ec2.py
  AWS_REGION = 'region名'
  TAG_KEY = 'TAG名'
$ python ./deploy_lambda_backup_ec2.py
```
## 注意点
VPCにLambdaを配置する場合、NATgatewayもしくはNATinstanceが必要です.

## その他
バックアップ対象のTag名があわない場合、backup_ec2.pyのTAG_KEY = を修正してください.

## 参考文献
[boto3](https://boto3.readthedocs.io/en/latest/index.html)  
[EC2のスナップショットを自動的にAWS Lambdaで作成する](http://qiita.com/eiroh/items/66bb68d12bd8fdbbd076)  
[AMIバックアップを取るLambdaファンクション](http://qiita.com/Hiroyama-Yutaka/items/9fab02438dc22c0b85ea)  

#### 免責事項  
自己責任でお願いします.

　　