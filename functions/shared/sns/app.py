import boto3
import json
import os
from aws_lambda_powertools import Logger

sns_client = boto3.client('sns')
ENV = os.environ['ENV']
logger = Logger()


def lambda_handler(event, context):
    try:
        sns_message = f"Gen AI stack job complete!"

        sns_response = sns_client.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=sns_message,
            Subject=sns_message
        )
        logger.info(f"sns publish response: {sns_response}")

    except Exception as e:
        logger.error(f"Error in publishing job completion SNS message: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully published job complete SNS message')
    }
