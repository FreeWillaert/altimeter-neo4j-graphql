#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from stacks.vpc_stack import VpcStack
from stacks.scanner_stack import ScannerStack
from stacks.neo4j_importer_stack import Neo4jImporterStack
from stacks.neo4j_stack import Neo4jStack


app = cdk.App()
vpc_stack = VpcStack(app, "AltimeterVpcStack")
neo4j_stack = Neo4jStack(app, "AltimeterNeo4jStack", vpc_stack.vpc)
scanner_stack = ScannerStack(app, "AltimeterScannerStack", vpc_stack.vpc)
neo4j_importer_stack = Neo4jImporterStack(app, "AltimeterNeo4jImporterStack", vpc_stack.vpc, scanner_stack.bucket, neo4j_stack.instance, neo4j_stack.neo4j_user_secret)


app.synth()
