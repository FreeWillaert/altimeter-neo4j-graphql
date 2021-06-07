import json
from os import name
import os.path

from aws_cdk import core as cdk
from aws_cdk.aws_ec2 import SubnetConfiguration, SubnetType, Vpc
from aws_cdk.aws_ecs import AwsLogDriver, Cluster, ContainerImage, FargateTaskDefinition, TaskDefinition
from aws_cdk.aws_iam import AccountPrincipal, ManagedPolicy, Role, ServicePrincipal
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_s3 import BlockPublicAccess, Bucket, BucketEncryption

CONFIG_FILENAME = "config.json"

class ScannerStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config = self.read_config()


        # TODO: See if this can also run in a private subnet...?
        vpc = Vpc(self, "ec2-vpc-altimeter",
            max_azs=1,
            subnet_configuration=[
                SubnetConfiguration(
                    name="Public", 
                    subnet_type=SubnetType.PUBLIC
                )
            ]
        )

        Bucket(self, "s3-bucket-altimeter", 
            bucket_name=config["s3_bucket"],
            encryption=BucketEncryption.S3_MANAGED,
            block_public_access=BlockPublicAccess.BLOCK_ALL
        )

        Cluster(self, "ecs-cluster-altimeter", 
            cluster_name="Altimeter",
            vpc=vpc               
        )

        # execution_role = Role(self, "iam-role-altimeter-execution-role",
        #     assumed_by=ServicePrincipal("ecs-tasks.amazonaws.com"),
        #     # It appears that within the account where the scanner is running, the execution role is (partially) used for scanning resources (rather than the altimeter-scanner-access role).      
        #     managed_policies=[
        #         ManagedPolicy.from_aws_managed_policy_name('SecurityAudit'),
        #         ManagedPolicy.from_aws_managed_policy_name('job-function/ViewOnlyAccess')
        #     ]
        # )

        task_role = Role(self, "iam-role-altimeter-task-role",
            assumed_by=ServicePrincipal("ecs-tasks.amazonaws.com"),
            # It appears that within the account where the scanner is running, the task role is (partially) used for scanning resources (rather than the altimeter-scanner-access role).      
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name('SecurityAudit'),
                ManagedPolicy.from_aws_managed_policy_name('job-function/ViewOnlyAccess')
            ]
        )

        task_definition = FargateTaskDefinition(self, "ecs-fgtd-altimeter",
            # execution_role=execution_role,
            task_role=task_role,
            memory_limit_mib=1024
        )

        docker_path = os.path.join(os.path.curdir,"..")

        image_asset = DockerImageAsset(self, 'ecr-assets-dia-altimeter', 
            directory=docker_path,
            file="scanner.Dockerfile"
        )            

        task_definition.add_container("ecs-container-altimeter",            
            image= ContainerImage.from_docker_image_asset(image_asset),
            memory_limit_mib=1024,
            cpu=256,
            environment= {
                "CONFIG_PATH": config["altimeter_config_path"],
                "S3_BUCKET": config["s3_bucket"]
            },
            logging= AwsLogDriver(
                stream_prefix= 'altimeter',
                log_retention= RetentionDays.TWO_WEEKS
            )
        )

        # task_definition.add_to_execution_role_policy()

        task_definition.add_to_task_role_policy(PolicyStatement(
            resources=["arn:aws:iam::*:role/"+config["account_execution_role"]],
            actions=['sts:AssumeRole']
        ))

        task_definition.add_to_task_role_policy(PolicyStatement(
            resources=[
                "arn:aws:s3:::"+config["s3_bucket"],
                "arn:aws:s3:::"+config["s3_bucket"]+"/*"
            ],
            actions=["s3:GetObject*",
                "s3:GetBucket*",
                "s3:List*",
                "s3:DeleteObject*",
                "s3:PutObject",
                "s3:Abort*",
                "s3:PutObjectTagging"]
        ))



        # Grant the ability to record the stdout to CloudWatch Logs
        # TODO: Refine?
        task_definition.add_to_task_role_policy(PolicyStatement(
            resources=["*"],
            actions=['logs:*']
        ))


    def read_config(self):
        if not os.path.isfile(CONFIG_FILENAME):
            print(f"Please provide a {CONFIG_FILENAME} file.")
        else:
            with open(CONFIG_FILENAME, "r") as f:
                config = json.loads(f.read())
                return config
        
