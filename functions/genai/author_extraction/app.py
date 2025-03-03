import boto3
import ast
import json
import statistics
import os
from aws_lambda_powertools import Logger
logger = Logger()

PATH = 'ner-model'
ENV = os.environ['ENV']
EXTRACTS_BUCKET = os.environ['EXTRACTS_BUCKET']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
ENDPOINT_NAME = f"{ENV}-{os.environ['ENDPOINT_NAME']}"

s3 = boto3.client('s3')
logger = Logger()
sagemaker = boto3.client('sagemaker-runtime')
first_page_chars = 1_500

def read_file_from_s3(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return obj['Body'].read().decode('utf-8', errors='ignore')


def concatenate_names(string_list):
    names = []

    for string in string_list:
        word = string.strip().replace("#", "")
        if word and word[0].isupper():
            names.append(word)
        else:
            if names:
                names[-1] += word
            else:
                names.append(word)

    full_name = " ".join(names)
    if full_name[0] == ".":
        full_name = full_name[1:]
    full_name = full_name.strip()
    return full_name


def get_names(ner_results):
    names = []
    _name = []
    b_scores = []
    i_scores = []
    prev_entity = 'B-PER'

    for result in ner_results:
        if float(result['score']) < .5:
            continue

        if (result['entity'] == 'B-PER') and result['word'].startswith("#"):
            result['entity'] = 'I-PER'

        if (result['entity'] == 'I-PER') or ((result['entity'] == 'B-PER') and (prev_entity in ['B-PER'])):
            _name.append(result['word'].strip())
            i_scores.append(result['score'])

        elif result['entity'] == 'B-PER':

            if len(_name) > 0:
                names.append(concatenate_names(_name))

            _name = [result['word'].strip()]
            b_scores.append(result['score'])

        if result['entity'] in ['B-PER', 'I-PER']:
            prev_entity = result['entity']

    if len(_name) > 0:
        names.append(concatenate_names(_name))

    names = list(set(names))
    logger.info(f"names: {names}")
    if len(b_scores) > 0:
        logger.info(f"b_scores: {statistics.mean(b_scores)}")
    else:
        logger.info(f"b_scores: 0")

    if len(i_scores) > 0:
        logger.info(f"i_scores: {statistics.mean(i_scores)}")
    else:
        logger.info(f"i_scores: 0")

    return names


def lambda_handler(event, context):
    file_name = event.get('uid')
    text = read_file_from_s3(EXTRACTS_BUCKET, file_name)

    payload = json.dumps({"inputs": text[:first_page_chars]})

    response = sagemaker.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        Body=payload,
        ContentType='application/json'
    )
    logger.info(f"response: {response}")

    ner_results = ast.literal_eval(response['Body'].read().decode('utf-8'))
    logger.info(f"ner_results: {ner_results}")

    names_str = ""
    if ner_results:
        names_list = get_names(ner_results)
        for name in names_list:
            names_str += name + "\n"

    logger.info(f"names_str: {names_str}")

    s3.put_object(
        Body=names_str,
        Bucket=OUTPUT_BUCKET,
        Key=file_name
    )

    return {
        'statusCode': 200,
        'uid': file_name,
        "MessageDetails": event.get("MessageDetails")
    }
