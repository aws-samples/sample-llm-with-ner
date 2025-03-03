import ast
import time

import boto3
import os
import logging
import json

ENV = os.environ.get('ENV')
CONTAINS_BUCKET = os.environ['CONTAINS_BUCKET']
DOES_NOT_CONTAIN_BUCKET = os.environ['DOES_NOT_CONTAIN_BUCKET']
NER_ENDPOINT_NAME = os.environ.get('NER_ENDPOINT_NAME', None)
LLM_ENDPOINT_NAME = os.environ.get('LLM_ENDPOINT_NAME', None)
CHECK_LLM_UP = ast.literal_eval(os.environ['CHECK_LLM_UP'])
PUSH_TO_QUEUE_LAMBDA = os.environ['PUSH_TO_QUEUE_LAMBDA']
BATCH_SIZE = int(os.environ['BATCH_SIZE'])

STATE_MACHINE_ARN = os.environ.get("GEN_AI_STATE_MACHINE_ARN", "NONE")
TIME_TO_LIVE_DAYS = int(os.environ.get("DOC_STATE_TTL_DAYS", 30))

NER_ENDPOINT_NAME = f"{ENV}-{NER_ENDPOINT_NAME}"
LLM_ENDPOINT_NAME = f"{ENV}-{LLM_ENDPOINT_NAME}"


class LambdaDynamoDBClass:
    """
    AWS DynamoDB Resource Class
    """
    def __init__(self, lambda_dynamodb_resource):
        """
        Initialize a DynamoDB Resource
        """
        self.resource = lambda_dynamodb_resource["resource"]
        self.table_name = lambda_dynamodb_resource["table_name"]
        self.table = self.resource.Table(self.table_name)


class LambdaSQSClass:
    """
    AWS SQS Resource Class
    """
    def __init__(self, lambda_sqs_resource):
        """
        Initialize an SQS Resource
        """
        self.resource = lambda_sqs_resource["resource"]
        self.queue_name = lambda_sqs_resource["queue_name"]
        self.queue = self.resource.Queue(self.queue_name)


s3 = boto3.client('s3')
sagemaker = boto3.client('sagemaker')
lambda_client = boto3.client('lambda')
sfn_client = boto3.client('stepfunctions')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _get_all_files_from_bucket(bucket):
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket)
    all_files = []

    for page in pages:
        for obj in page.get('Contents', []):
            all_files.append(obj['Key'])

    all_files = [x for x in all_files if x is not None]

    logger.info(f'Number of files in {bucket}: {len(all_files)}')
    return all_files


def _list_set_difference(list_1, list_2):
    set_1 = set(list_1)
    set_2 = set(list_2)
    return list(set_1 - set_2)


def _check_llm_up(endpoint_name):
    if not endpoint_name:
        return False

    logger.info(f'Checking if endpoint {endpoint_name} is up...')
    try:
        response = sagemaker.describe_endpoint(
            EndpointName=endpoint_name
        )

    except sagemaker.exceptions.ClientError as client_error:
        logger.error(f'Error: {client_error}')
        response = {'EndpointStatus': "NotInService"}

    llm_up = response['EndpointStatus'] == 'InService'
    logger.info(f'{endpoint_name} is up: {llm_up}')

    return llm_up


def single_list_to_list_of_lists(single_list, inner_list_size=10):
    return [single_list[i:i + inner_list_size] for i in range(0, len(single_list), inner_list_size)]


def lambda_handler(event, context):
    logger.info(f'CHECK_LLM_UP: {CHECK_LLM_UP}')
    contains_bucket_files = _get_all_files_from_bucket(CONTAINS_BUCKET)
    does_not_contains_bucket_files = _get_all_files_from_bucket(DOES_NOT_CONTAIN_BUCKET)

    files_to_process = _list_set_difference(
        list_1=contains_bucket_files,
        list_2=does_not_contains_bucket_files
    )
    logger.info(f'Number of files to process: {len(files_to_process)}')
    logger.info(f'BATCH_SIZE: {BATCH_SIZE}')

    if not CHECK_LLM_UP or (_check_llm_up(LLM_ENDPOINT_NAME) and _check_llm_up(NER_ENDPOINT_NAME)):
        responses = []
        files_to_process = single_list_to_list_of_lists(
            single_list=files_to_process,
            inner_list_size=BATCH_SIZE
        )
        logger.info(f'Number of batches: {len(files_to_process)}')

        for index, list_of_files in enumerate(files_to_process):
            lambda_client.invoke(
                FunctionName=PUSH_TO_QUEUE_LAMBDA,
                Payload=json.dumps(list_of_files),
                InvocationType='Event'
            )
            logger.info(f"files pushing to queue via push_to_queue lambda: {(index + 1) * len(list_of_files)}")

        time.sleep(30)  # adjust as needed
        logger.info(f"Triggering step function...")
        response = sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps({})
        )  

        return {
            'statusCode': 200,
            'headers': {
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
            },
            'body': json.dumps({
                'responses': responses           
            }),
        }

    else:
        return {
            'statusCode': 500,
            'body': json.dumps({
              "error": "LLMs not up"
            }),
        }

    

