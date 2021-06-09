import json
import urllib.parse
import boto3
import logging

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

        logger.info(raw_file_content)

        prepared_file_content = raw_file_content.replace(
            '<ns1:last_ip rdf:datatype="http://www.w3.org/2001/XMLSchema#nonNegativeInteger">340282366920938463463374607431768211455</ns1:last_ip>',
            '<ns1:last_ip>340282366920938463463374607431768211455</ns1:last_ip>')

        logger.info(prepared_file_content)
        
        prepared_file_key = key.replace('/raw','/prepared')

        s3.put_object(Body=prepared_file_content, Bucket=bucket, Key=key)

        logger.info("object put")

        return "OK"
    except Exception as e:
        logger.error(e)
        print('Error getting object {} from bucket {}. Make sure the object exists and your bucket is in the same region as this function.'.format(key, bucket))
        raise e