from aws_cdk import core as cdk
from aws_cdk.aws_ec2 import IVpc, IInstance, Instance, SubnetSelection
from aws_cdk.aws_iam import Role
from aws_cdk.aws_lambda import Runtime, Function
from aws_cdk.aws_lambda_python import PythonFunction
from aws_cdk.aws_s3 import IBucket

from .config import read_config

NEO4J_USER_SECRET_NAME = "secret-altimeter-neo4j-user"

class Neo4jImporterStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc: IVpc, bucket: IBucket, instance: IInstance, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config = read_config()

        neo4j_importer_function = PythonFunction(self, 'lambda-function-neo4j-importer', 
            entry="../neo4j-importer",
            index="app.py",
            handler="lambda_handler",
            runtime=Runtime.PYTHON_3_8,
            memory_size=1024,
            timeout=cdk.Duration.seconds(60),
            vpc=vpc,
            # vpc_subnets=SubnetSelection(subnets=vpc.select_subnets(subnet_group_name='Private').subnets),
            vpc_subnets=SubnetSelection(subnets=vpc.select_subnets(subnet_group_name='Public').subnets), # TESTING
            environment={
                "neo4j_address": instance.instance_private_ip
            },
            allow_public_subnet=True # CDK Nagging
        )

        # TODO: Trigger function by S3 event
        

        role: Role = neo4j_importer_function.role
        bucket.grant_read_write(role)
