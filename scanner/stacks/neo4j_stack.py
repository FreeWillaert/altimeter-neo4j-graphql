from aws_cdk import core as cdk
from aws_cdk.aws_ec2 import BlockDevice, BlockDeviceVolume, EbsDeviceVolumeType, IVpc, IInstance, Instance, InstanceClass, InstanceSize, InstanceType, MachineImage, Peer, Port, SecurityGroup, SubnetConfiguration, SubnetSelection, SubnetType, UserData, Vpc
from aws_cdk.aws_iam import CfnInstanceProfile, ManagedPolicy, PolicyDocument, PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_secretsmanager import Secret

from .config import read_config

NEO4J_USER_SECRET_NAME = "secret-altimeter-neo4j-user"

class Neo4jStack(cdk.Stack):

    instance: IInstance

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc: IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config = read_config()

        neo4j_user_secret = Secret(self,'secretsmanager-secret-neo4j-user',
            secret_name=NEO4J_USER_SECRET_NAME
        )
       
        neo4j_server_instance_role = Role(self,'iam-role-neo4j-server-instance',
            assumed_by=ServicePrincipal('ec2.amazonaws.com'),
            managed_policies=[
                ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'), # Use SSM Session Manager rather than straight ssh
                ManagedPolicy.from_aws_managed_policy_name('CloudWatchAgentServerPolicy')
            ],
            inline_policies={
                "work-with-tags": PolicyDocument(
                    statements=[
                        PolicyStatement(
                            actions=[
                                'ec2:CreateTags',
                                'ec2:Describe*',
                                # 'ec2:CreateVolume',
                                # 'ec2:AttachVolume',
                                'elasticloadbalancing:Describe*',
                                'cloudwatch:ListMetrics',
                                'cloudwatch:GetMetricStatistics',
                                'cloudwatch:Describe*',
                                'autoscaling:Describe*',
                                # 'route53:List*',
                                # 'route53:Read*',
                                # 'route53:ChangeResourceRecordSets'
                            ],
                            resources=["*"]
                        )
                    ]
                ),
                "access-neo4j-user-secret": PolicyDocument(
                    statements=[
                        PolicyStatement(
                            actions=['secretsmanager:GetSecretValue'],
                            resources=[neo4j_user_secret.secret_arn]
                        )
                    ]
                )
            }
        )

        instance_security_group = SecurityGroup(self, "ec2-sg-neo4j-server-instance",
            description="Neo4j Server Instance",
            vpc=vpc
        )

        # instance_security_group.add_ingress_rule(Peer.ipv4(vpc.vpc_cidr_block), Port.tcp(7687), 'Bolt from within own VPC')
        instance_security_group.add_ingress_rule(Peer.ipv4("0.0.0.0/0"), Port.tcp(7687), 'Bolt from ANYWHERE') # TESTING
        instance_security_group.add_ingress_rule(Peer.ipv4("0.0.0.0/0"), Port.tcp(7473), 'Bolt from ANYWHERE') # TESTING

        # Prepare userdata script
        with open("./resources/neo4j-server-instance-userdata.sh", "r") as f:
            userdata_content = f.read()
        userdata_content = userdata_content.replace("[[NEO4J_USER_SECRET_NAME]]",NEO4J_USER_SECRET_NAME)
        user_data = UserData.for_linux()
        user_data.add_commands(userdata_content)

        instance_type = InstanceType.of(InstanceClass.BURSTABLE2, InstanceSize.MEDIUM)

        self.instance = Instance(self, 'ec2-instance-neo4j-server-instance',
            instance_name="neo4j-community-standalone-server",
            machine_image=MachineImage.generic_linux(
                ami_map={
                    "eu-west-1": "ami-00c8631d384ad7c53"
                }
            ),
            instance_type=instance_type,
            role=neo4j_server_instance_role,
            vpc=vpc,
            # vpc_subnets=SubnetSelection(subnets=vpc.select_subnets(subnet_group_name='Private').subnets),
            vpc_subnets=SubnetSelection(subnets=vpc.select_subnets(subnet_group_name='Public').subnets), # TESTING
            security_group=instance_security_group,
            user_data=user_data,
            block_devices=[
                BlockDevice(
                    device_name="/dev/sda1",
                    volume=BlockDeviceVolume.ebs(
                        volume_size=10,
                        volume_type=EbsDeviceVolumeType.GP2,
                        encrypted=True, # Just encrypt
                        delete_on_termination=True
                    )                    
                ),
                BlockDevice(
                    device_name="/dev/sdb",
                    volume=BlockDeviceVolume.ebs(
                        volume_size=20, # TODO: Check size requirements
                        volume_type=EbsDeviceVolumeType.GP2,
                        encrypted=True,
                        delete_on_termination=True # ASSUMPTION: NO 'primary' data, only altimeter results.
                    )                    
                )
            ]
        )

        cdk.Tags.of(self.instance).add("neo4j_mode", "SINGLE")
        cdk.Tags.of(self.instance).add("dbms_mode", "SINGLE")

