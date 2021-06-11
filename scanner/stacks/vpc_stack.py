
from aws_cdk import core as cdk
from aws_cdk.aws_ec2 import IVpc, SubnetConfiguration, SubnetType, Vpc

from .config import read_config

class VpcStack(cdk.Stack):

    vpc: IVpc

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = Vpc(self, "ec2-vpc-altimeter",
            max_azs=1,
            subnet_configuration=[
                SubnetConfiguration(
                    name="Public", 
                    subnet_type=SubnetType.PUBLIC
                ),
                SubnetConfiguration(
                    name="Private", 
                    subnet_type=SubnetType.PRIVATE
                )
            ]
        )