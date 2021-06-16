from typing import List
from aws_cdk.aws_lambda import Runtime

import jsii
from aws_cdk import core as cdk
from aws_cdk import aws_lambda_nodejs
from aws_cdk.aws_ec2 import IInstance, IVpc, SubnetSelection
from aws_cdk.aws_secretsmanager import ISecret
from aws_cdk.aws_lambda_nodejs import ICommandHooks, NodejsFunction, BundlingOptions
from aws_cdk.aws_apigateway import ApiKeySourceType, LambdaRestApi
class GraphqlApiStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, config, vpc: IVpc, instance: IInstance, neo4j_user_secret: ISecret, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        graphql_api_function = NodejsFunction(self, 'lambda-function-graphql-api',
            runtime=Runtime.NODEJS_12_X, # TODO: Check out if NODEJS_14_X also works with graphql handler.
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
                target= 'es2018',                
                command_hooks=self.CommandHooks(),
                node_modules=[
                    "apollo-server",
                    "apollo-server-lambda",
                    "graphql",
                    "lodash",
                    "neo4j-driver",
                    "neo4j-graphql-js"
                ]
                # ,
                # external_modules=[
                #     '@vue/compiler-sfc' # This causes trouble when handled by esbuild, and should not be needed.
                # ]
            )
        )

        # Grant lambda read access to the neo4j user secret
        neo4j_user_secret.grant_read(graphql_api_function.role)

        api = LambdaRestApi(self, 'apigateway-api-altimeter-graphql',
            handler=graphql_api_function,            
            proxy=False
        )

        items = api.root.add_resource('graphql');
        items.add_method('GET')
        items.add_method('POST')


    @jsii.implements(ICommandHooks)
    class CommandHooks:
        def before_install(self, input_dir: str, output_dir: str):
            return []

        def before_bundling(self, input_dir: str, output_dir: str):
            return []

        def after_bundling(self, input_dir: str, output_dir: str):
            commands: List[str] = [] 
            commands.append(f"cp {input_dir}/../graphql-api/schema.graphql {output_dir}")
            commands.append("echo 'AFTER BUNDLING COMMANDS DONE'")
            return commands
