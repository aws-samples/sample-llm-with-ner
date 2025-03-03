import logging
import os
import aws_sqs_batchlib

ENV = os.environ.get('ENV')
SQS_URL = os.environ.get("FILE_SQS_QUEUE_NAME", "NONE")
MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY", 100))

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(event)

    res = aws_sqs_batchlib.receive_message(
        QueueUrl=SQS_URL,
        MaxNumberOfMessages=MAX_CONCURRENCY,
        
    )
    return res
