import boto3
import os
import logging
import json
import datetime

LAMBDA_DYNAMODB_RESOURCE = {
    "resource": boto3.resource('dynamodb'),
    "table_name": os.environ.get("DOC_DDB_STATE_TABLE", "NONE")
}

LAMBDA_SQS_RESOURCE = {
    "resource": boto3.resource('sqs'),
    "queue_name": os.environ.get("FILE_SQS_QUEUE_NAME", "NONE")
}

STATE_MACHINE_ARN = os.environ.get("GEN_AI_STATE_MACHINE_ARN", "NONE")
TIME_TO_LIVE_DAYS = int(os.environ.get("DOC_STATE_TTL_DAYS", 30))


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

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    files_to_process = event
    expiry = int((datetime.datetime.now() + datetime.timedelta(days=TIME_TO_LIVE_DAYS)).timestamp())

    sqs = LambdaSQSClass(LAMBDA_SQS_RESOURCE)
    queue_url = sqs.queue.url
    responses = []

    for index, file in enumerate(files_to_process):
        logger.info(f"Processing file: {file} [{(index+1)}/{len(files_to_process)}]")
        ddb_state_resource = LambdaDynamoDBClass(LAMBDA_DYNAMODB_RESOURCE)

        logger.info(f"Adding file to Dynamo: {file}")
        table = ddb_state_resource.table
        # Set expiration

        table.put_item(
            Item={
                's3_path': file,
                'status': "INGESTED",
                'ttl': expiry
            }
        )

        message = json.dumps({
            'uid': file,
        })

        logger.info("Adding Message to SQS Queue for file: %s" % file)
        sqs_response = sqs.queue.send_message(
            QueueUrl=queue_url,
            MessageBody=message
        )

        responses.append({
            'uid': file,
            'message': message,
            'sqs_response_md5': sqs_response['MD5OfMessageBody']
        })
        logger.info("Successfully added Message to SQS Queue for file: %s" % file)

    return {
        'statusCode': 200,  # accepted
        'headers': {
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        'body': json.dumps({
            'responses': responses
        }),
    }
