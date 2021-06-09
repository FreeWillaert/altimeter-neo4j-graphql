#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from stacks.vpc_stack import VpcStack
from stacks.scanner_stack import ScannerStack
from stacks.neo4j_stack import Neo4jStack


app = cdk.App()
vpc_stack = VpcStack(app, "AltimeterVpcStack")
neo4j_stack = Neo4jStack(app, "AltimeterNeo4jStack", vpc_stack.vpc)
ScannerStack(app, "AltimeterScannerStack", vpc_stack.vpc,
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    #env=core.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    #env=core.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
