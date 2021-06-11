import os.path

from aws_cdk import core as cdk
from aws_cdk.aws_ec2 import IVpc, SubnetSelection, SubnetType
from aws_cdk.aws_ecs import AwsLogDriver, Cluster, ContainerImage, FargateTaskDefinition, TaskDefinition
from aws_cdk.aws_iam import ManagedPolicy, PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_cdk.aws_events import EventPattern, Rule, Schedule
from aws_cdk.aws_events_targets import EcsTask
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_s3 import BlockPublicAccess, Bucket, BucketEncryption, IBucket

from .config import read_config

class ScannerStack(cdk.Stack):

    bucket: IBucket

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc: IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config = read_config()

        self.bucket = Bucket(self, "s3-bucket-altimeter", 
            bucket_name=config["s3_bucket"],
            encryption=BucketEncryption.S3_MANAGED,
            block_public_access=BlockPublicAccess.BLOCK_ALL
        )

        cluster = Cluster(self, "ecs-cluster-altimeter", 
            cluster_name="Altimeter",
            vpc=vpc               
        )

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

        # Trigger task every 24 hours
        Rule(self, "events-rule-altimeter-daily-scan",
            rule_name="evrule--altimeter-daily-scan",
            schedule=Schedule.cron(hour="0", minute="0"),
            description="Daily altimeter scan",
            targets=[EcsTask(
                task_definition=task_definition,
                cluster=cluster,
                subnet_selection=SubnetSelection(subnet_type=SubnetType.PRIVATE)
            )]
        )

        # Trigger task manually via event
        Rule(self, "events-rule-altimeter-manual-scan",
            rule_name="evrule--altimeter-manual-scan",
            event_pattern=EventPattern(source=['altimeter']), 
            description="Manual altimeter scan",
            targets=[EcsTask(
                task_definition=task_definition,
                cluster=cluster,
                subnet_selection=SubnetSelection(subnet_type=SubnetType.PRIVATE)
            )]
        )        



        
