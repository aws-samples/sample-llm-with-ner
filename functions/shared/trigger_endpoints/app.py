import boto3
import os
import json

from aws_lambda_powertools import Logger
logger = Logger()

lambda_client = boto3.client('lambda')

LLM_LAMBDA = os.environ['LLM_LAMBDA']
NER_LAMBDA = os.environ['NER_LAMBDA']

logger.info(f"LLM_LAMBDA: {LLM_LAMBDA}")
logger.info(f"NER_LAMBDA: {NER_LAMBDA}")


def lambda_handler(event, context):
    try:
        llm = lambda_client.invoke(
            FunctionName=LLM_LAMBDA,
            InvocationType='Event'
        )
    
        logger.info(f"LLM invoked: {llm}")
    
        ner = lambda_client.invoke(
            FunctionName=NER_LAMBDA,
            InvocationType='Event'
        )

        logger.info(f"NER invoked: {ner}")

        return {
            'statusCode': 200,
            'body': json.dumps(f'Both SageMaker Create Endpoint Lambda functions triggered.')
        }
        
    except Exception as e:
        logger.info(f"Error invoking Lambda functions: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }