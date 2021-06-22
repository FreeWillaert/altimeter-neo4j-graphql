#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from stacks.vpc_stack import VpcStack
from stacks.scanner_stack import ScannerStack
from stacks.neo4j_stack import Neo4jStack
from stacks.graphql_api_stack import GraphqlApiStack

from stacks.config import read_config


app = cdk.App()

config = read_config()

vpc_stack = VpcStack(app, "stack-altimeter--vpc", config)
neo4j_stack = Neo4jStack(app, "stack-altimeter--neo4j", config, vpc_stack.vpc)
scanner_stack = ScannerStack(app, "stack-altimeter--scanner", config, vpc_stack.vpc, neo4j_stack.instance, neo4j_stack.neo4j_user_secret)
graphql_api_stack = GraphqlApiStack(app,"stack-altimeter--graphql-api", config, vpc_stack.vpc, neo4j_stack.instance, neo4j_stack.neo4j_user_secret)

app.synth()
