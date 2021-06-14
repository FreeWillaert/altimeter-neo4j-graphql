import json

from typing import Dict, List
from aws_cdk import core as cdk
from aws_cdk import aws_lambda_nodejs
from aws_cdk.aws_ec2 import IInstance, IVpc, SubnetSelection
from aws_cdk.aws_secretsmanager import ISecret
from aws_cdk.aws_lambda_nodejs import ICommandHooks, NodejsFunction, BundlingOptions
import jsii

# NEO4J_USER_SECRET_NAME = "secret-altimeter-neo4j-user"


class GraphqlApiStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, config, vpc: IVpc, instance: IInstance, neo4j_user_secret: ISecret, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        function = NodejsFunction(self, 'lambda-function-graphql-api',
            # function_name=
            entry='../graphql-api/app.ts',
            memory_size=256,
            timeout=cdk.Duration.seconds(10),
            vpc=vpc,
            vpc_subnets=SubnetSelection(subnets=vpc.select_subnets(subnet_group_name='Private').subnets),
            environment={
                "neo4j_address": instance.instance_private_ip,
                "neo4j_user_secret_name": neo4j_user_secret.secret_name
            },
            bundling=BundlingOptions(
                source_map=True,
                target= 'es2020',
                command_hooks=self.CommandHooks()
            )
        )

    @jsii.implements(ICommandHooks)
    class CommandHooks:
        def before_bundling(self, input_dir: str, output_dir: str):
            return []

        def after_bundling(self, input_dir: str, output_dir: str):
            commands: List[str] = [] 
            # TODO: Actually need config.json?
            commands.append(f"cp {input_dir}/../graphql-api/config.json {output_dir}")
            commands.append(f"cp {input_dir}/../graphql-api/schema.graphql {output_dir}")
            commands.append("echo 'AFTER BUNDLING COMMANDS DONE'")
            return commands

