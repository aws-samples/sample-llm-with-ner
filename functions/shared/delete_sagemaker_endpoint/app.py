import boto3
import json
import os

from aws_lambda_powertools import Logger
logger = Logger()

client = boto3.client('sagemaker')
sns_client = boto3.client('sns')
ENV = os.environ['ENV']
MODEL_NAME = os.environ['MODEL_NAME']
ENDPOINT_CONFIG_NAME = os.environ['ENDPOINT_CONFIG_NAME']
ENDPOINT_NAME = os.environ['ENDPOINT_NAME']

MODEL_NAME = f"{ENV}-{MODEL_NAME}"
ENDPOINT_CONFIG_NAME = f"{ENV}-{ENDPOINT_CONFIG_NAME}"
ENDPOINT_NAME = f"{ENV}-{ENDPOINT_NAME}"


def lambda_handler(event, context):
    try:
        logger.info(f"Deleting {ENDPOINT_NAME} endpoint")
        response = client.delete_endpoint(EndpointName=ENDPOINT_NAME)
        logger.info(f"delete_endpoint API response: {response}")

        # SNS message
        sns_message = f"SageMaker endpoint '{ENDPOINT_NAME}' is being deleted."

        sns_response = sns_client.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=sns_message,
            Subject=f'SageMaker Endpoint Deletion Notification: {ENDPOINT_NAME}',
        )
        logger.info(f"sns publish response: {sns_response}")
        print('SNS message published')
    except Exception as e:
        logger.error(f"Error in deleting {ENDPOINT_NAME} endpoint: {e}")

    try:
        logger.info(f"Deleting {ENDPOINT_CONFIG_NAME} endpoint config")
        response = client.delete_endpoint_config(EndpointConfigName=ENDPOINT_CONFIG_NAME)
        logger.info(f"delete_endpoint_config API response: {response}")
    except Exception as e:
        logger.error(f"Error in deleting {ENDPOINT_NAME} endpoint: {e}")

    try:
        logger.info(f"Deleting {MODEL_NAME} model")
        response = client.delete_model(ModelName=MODEL_NAME)
        logger.info(f"delete_model API response: {response}")
    except Exception as e:
        logger.error(f"Error in deleting {MODEL_NAME} endpoint: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully initiated {ENDPOINT_NAME} Endpoint deletion')
    }
