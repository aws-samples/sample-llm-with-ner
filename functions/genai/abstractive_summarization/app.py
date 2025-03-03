import boto3
import ast
import json
import os
from aws_lambda_powertools import Logger

logger = Logger()

ENV = os.environ['ENV']
ENDPOINT_NAME = f"{ENV}-{os.environ['ENDPOINT_NAME']}"
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
EXTRACTIVE_SUMMARY_BUCKET = os.environ['EXTRACTIVE_SUMMARY_BUCKET']
sagemaker = boto3.client('sagemaker-runtime')

s3 = boto3.client('s3')
char_count = 10_000


def read_file_from_s3(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj['Body'].read().decode('utf-8', errors='ignore')


def lambda_handler(event, context):
    file_name = event.get('uid')
    logger.info(f"file_name: {file_name}")

    text = read_file_from_s3(EXTRACTIVE_SUMMARY_BUCKET, file_name)
    inputs = f'<s>[INST] <<SYS>>\nWrite an abstract given the following text\n<</SYS>>\n\n{text[:char_count]} [/INST]'
    logger.info(f"inputs: {inputs}")

    payload = json.dumps(
        {
            "inputs": inputs,
            "parameters": {
                "max_new_tokens": 512,
                "top_p": 0.1,
                "temperature": 0.1
            }
        }
    )

    response = sagemaker.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        Body=payload,
        ContentType='application/json'
    )

    response = response['Body'].read().decode('utf-8')
    summary = ast.literal_eval(response)[0]['generated_text'][len(inputs):]
    logger.info(f"summary: {summary}")

    s3.put_object(
        Body=summary,
        Bucket=OUTPUT_BUCKET,
        Key=file_name
    )

    return {
        'statusCode': 200,
        'uid': file_name,
        "MessageDetails": event.get("MessageDetails")
    }
