import json
import urllib.parse
import os
import boto3
import logging

from neo4j import GraphDatabase

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')

s3 = boto3.client('s3')

def lambda_handler(event, context):
    logger.info("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        logger.info("reading object")

        raw_file_object = s3.get_object(Bucket=bucket, Key=key)
        logger.info("CONTENT TYPE: " + raw_file_object['ContentType'])

        raw_file_content = raw_file_object['Body'].read().decode('utf-8')

        logger.info("raw file read")
        # logger.info(raw_file_content)

        prepared_file_content = raw_file_content.replace(
            '<ns1:last_ip rdf:datatype="http://www.w3.org/2001/XMLSchema#nonNegativeInteger">340282366920938463463374607431768211455</ns1:last_ip>',
            '<ns1:last_ip>340282366920938463463374607431768211455</ns1:last_ip>')

        # logger.info(prepared_file_content)
        
        prepared_file_key = key.replace('raw/','prepared/')

        s3.put_object(Body=prepared_file_content, Bucket=bucket, Key=prepared_file_key)

        logger.info("prepared file written")

        rdf_presigned_url = s3.generate_presigned_url(
            ClientMethod='get_object', 
            Params={'Bucket': bucket, 'Key': prepared_file_key},
            ExpiresIn=3600
        )

        logger.info("presigned url: " + rdf_presigned_url)

         # TODO: Get neo4j address and password
        neo4j_address = "10.0.108.245"
        neo4j_user_password = os.environ['TEMP_neo4j_password']

        neo4j_driver = GraphDatabase.driver(f"neo4j://{neo4j_address}:7687", auth=("neo4j", neo4j_user_password))
        logger.info("neo4j driver initialized")

        with neo4j_driver.session() as session:
            session.write_transaction(clear_rdf)
            logger.info("cleared")
            session.write_transaction(import_rdf, rdf_presigned_url)
            logger.info("imported")


        neo4j_driver.close()

        return "OK"
    except Exception as e:
        logger.error(e)
        raise e

def clear_rdf(tx):
    tx.run("MATCH (resource:Resource) DETACH DELETE resource")

def import_rdf(tx, rdf_presigned_url):
    tx.run("CALL n10s.rdf.import.fetch([rdf_url], \"RDF/XML\")")
