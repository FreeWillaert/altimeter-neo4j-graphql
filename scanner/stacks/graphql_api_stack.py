from typing import List
from aws_cdk.aws_lambda import Runtime

import jsii
from aws_cdk import core as cdk
from aws_cdk import aws_lambda_nodejs
from aws_cdk.aws_ec2 import IInstance, IVpc, SubnetSelection
from aws_cdk.aws_secretsmanager import ISecret
from aws_cdk.aws_lambda_nodejs import ICommandHooks, NodejsFunction, BundlingOptions
from aws_cdk.aws_apigateway import ApiKeySourceType, Cors, CorsOptions, LambdaRestApi
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
                    # Something goes wrong when these modules are bundled
                    "graphql",
                    "neo4j-graphql-js" 
                ]
            )
        )

        # Grant lambda read access to the neo4j user secret
        neo4j_user_secret.grant_read(graphql_api_function.role)

        api = LambdaRestApi(self, 'apigateway-api-altimeter-graphql',
            handler=graphql_api_function,            
            proxy=False
        )

        # Minimal security: Require an API key - use must go get the key value and configure its browser to send it along.
        default_key = api.add_api_key('default')
        default_usage_plan = api.add_usage_plan('apigateway-usageplan-altimeter-graphql', name='default')
        default_usage_plan.add_api_key(default_key)
        default_usage_plan.add_api_stage(stage=api.deployment_stage)

        items = api.root.add_resource('graphql',
            default_cors_preflight_options=CorsOptions(
                allow_origins=Cors.ALL_ORIGINS, # TODO: Limit to GUI?
                allow_methods=['GET','POST']
            )
        )
        items.add_method('GET', api_key_required=True)
        items.add_method('POST', api_key_required=True)

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

