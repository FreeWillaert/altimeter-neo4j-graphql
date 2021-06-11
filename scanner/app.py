#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from stacks.vpc_stack import VpcStack
from stacks.scanner_stack import ScannerStack
from stacks.neo4j_stack import Neo4jStack

from stacks.config import read_config


app = cdk.App()

config = read_config()

vpc_stack = VpcStack(app, "AltimeterVpcStack", config)
neo4j_stack = Neo4jStack(app, "AltimeterNeo4jStack", config, vpc_stack.vpc)
scanner_stack = ScannerStack(app, "AltimeterScannerStack", config, vpc_stack.vpc, neo4j_stack.instance, neo4j_stack.neo4j_user_secret)

app.synth()
