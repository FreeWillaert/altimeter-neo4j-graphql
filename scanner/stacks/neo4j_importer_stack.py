from aws_cdk import core as cdk
from aws_cdk.aws_ec2 import IVpc, IInstance, Instance, SubnetSelection
from aws_cdk.aws_iam import Role
from aws_cdk.aws_lambda import Runtime, Function, IFunction
from aws_cdk.aws_lambda_event_sources import S3EventSource
from aws_cdk.aws_lambda_python import PythonFunction
from aws_cdk.aws_s3 import IBucket, EventType
from aws_cdk.aws_secretsmanager import ISecret

from .config import read_config

NEO4J_USER_SECRET_NAME = "secret-altimeter-neo4j-user"

neo4j_importer_function: IFunction

class Neo4jImporterStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, vpc: IVpc, bucket: IBucket, instance: IInstance, neo4j_user_secret: ISecret, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        config = read_config()

        self.neo4j_importer_function = PythonFunction(self, 'lambda-function-neo4j-importer', 
            entry="../neo4j-importer",
            index="app.py",
            handler="lambda_handler",
            runtime=Runtime.PYTHON_3_8,
            memory_size=256,
            timeout=cdk.Duration.seconds(60),
            vpc=vpc,
            vpc_subnets=SubnetSelection(subnets=vpc.select_subnets(subnet_group_name='Private').subnets),
            environment={
                "neo4j_address": instance.instance_private_ip,
                "neo4j_user_secret_name": neo4j_user_secret.secret_name
            }
        )

        # neo4j_importer_function.add_event_source(
        #     S3EventSource(bucket,
        #         events= [EventType.OBJECT_CREATED, EventType.OBJECT_REMOVED],
        #         filters= [ { "prefix": "raw/", "suffix": ".rdf"}]
        #     )
        # )

        # Grant lambda read/write access to the S3 bucket for reading raw rdf, writing prepared rdf and generating signed uri
        bucket.grant_read_write(self.neo4j_importer_function.role)
        neo4j_user_secret.grant_read(self.neo4j_importer_function.role)
