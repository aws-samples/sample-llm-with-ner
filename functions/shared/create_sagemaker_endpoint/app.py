import boto3
import ast
import json
import os
from aws_lambda_powertools import Logger
logger = Logger()

client = boto3.client('sagemaker')

ENV = os.environ['ENV']
MODEL_NAME = os.environ['MODEL_NAME']
ENDPOINT_NAME = os.environ['ENDPOINT_NAME']
ENDPOINT_CONFIG_NAME = os.environ['ENDPOINT_CONFIG_NAME']
LLM_WEIGHTS_BUCKET = os.environ['LLM_WEIGHTS_BUCKET']
CREATE_MODEL_ROLE_ARN = os.environ['CREATE_MODEL_ROLE_ARN']
AWS_REGION_NAME = os.environ['AWS_REGION_NAME']
SUBNETS = os.environ['SUBNETS']
SECURITY_GROUPS = os.environ['SECURITY_GROUPS']
MODEL_PATHS = os.environ['MODEL_PATHS']
DLC_ACCOUNTS_BY_REGION = os.environ['DLC_ACCOUNTS_BY_REGION']
MODEL_IMAGES = os.environ['MODEL_IMAGES']
MODEL_TYPE = os.environ['MODEL_TYPE']
MODEL_INSTANCE_TYPES = os.environ['MODEL_INSTANCE_TYPES']

MODEL_IMAGES = ast.literal_eval(MODEL_IMAGES)
MODEL_IMAGE = MODEL_IMAGES[MODEL_TYPE]

DLC_ACCOUNTS_BY_REGION = ast.literal_eval(DLC_ACCOUNTS_BY_REGION)
DLC_AWS_ACCOUNT_ID = DLC_ACCOUNTS_BY_REGION[AWS_REGION_NAME]

MODEL_PATHS = ast.literal_eval(MODEL_PATHS)
MODEL_INSTANCE_TYPES = ast.literal_eval(MODEL_INSTANCE_TYPES)

if MODEL_TYPE == "llm":
    ENVIRONMENT = {
        'HF_MODEL_ID': "/opt/ml/model",
        'SM_NUM_GPUS': json.dumps(8),
        "MAX_INPUT_LENGTH": "16000",
        "MAX_TOTAL_TOKENS": "20000",
        "MAX_BATCH_PREFILL_TOKENS": "18000",
    }
    MODEL_INSTANCE_TYPE = MODEL_INSTANCE_TYPES["llm"]
    MODEL_PATH = MODEL_PATHS['llm']

# Use NER model
else:
    ENVIRONMENT = {}
    MODEL_INSTANCE_TYPE = MODEL_INSTANCE_TYPES["ner"]
    MODEL_PATH = MODEL_PATHS['ner']

MODEL_NAME = f"{ENV}-{MODEL_NAME}"
ENDPOINT_CONFIG_NAME = f"{ENV}-{ENDPOINT_CONFIG_NAME}"
ENDPOINT_NAME = f"{ENV}-{ENDPOINT_NAME}"
IMAGE = f'{DLC_AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION_NAME}.amazonaws.com/{MODEL_IMAGE}'
MODEL_DATA_URL = f's3://{LLM_WEIGHTS_BUCKET}/{MODEL_PATH}'

logger.info(f"MODEL_PATH:{MODEL_PATH}")
logger.info(f"MODEL_NAME: {MODEL_NAME}")
logger.info(f"IMAGE: {IMAGE}")
logger.info(f"MODEL_DATA_URL: {MODEL_DATA_URL}")
logger.info(f"ENVIRONMENT: {ENVIRONMENT}")
logger.info(f"ENDPOINT_CONFIG_NAME: {ENDPOINT_CONFIG_NAME}")
logger.info(f"ENDPOINT_NAME: {ENDPOINT_NAME}")


def lambda_handler(event, context):
    create_model_api_response = client.create_model(
        ModelName=MODEL_NAME,
        PrimaryContainer={
            'Image': IMAGE,
            'ModelDataUrl': MODEL_DATA_URL,
            'Environment': ENVIRONMENT
        },
        ExecutionRoleArn=CREATE_MODEL_ROLE_ARN,
        VpcConfig={
           'SecurityGroupIds': SECURITY_GROUPS.split(","),
           'Subnets': SUBNETS.split(",")
           }
    )

    logger.info("create_model API response", create_model_api_response)

    # create sagemaker endpoint config
    create_endpoint_config_api_response = client.create_endpoint_config(
        EndpointConfigName=ENDPOINT_CONFIG_NAME,
        ProductionVariants=[
            {
                'VariantName': f'{MODEL_NAME}-Variant',
                'ModelName': MODEL_NAME,
                'InitialInstanceCount': 1,
                'InstanceType': MODEL_INSTANCE_TYPE,
                'ModelDataDownloadTimeoutInSeconds': 3600,
                # 'ContainerStartupHealthCheckTimeoutInSeconds': 3600
            },
        ]
    )

    logger.info("create_endpoint_config API response", create_endpoint_config_api_response)

    # create sagemaker endpoint
    create_endpoint_api_response = client.create_endpoint(
        EndpointName=ENDPOINT_NAME,
        EndpointConfigName=ENDPOINT_CONFIG_NAME,
    )

    logger.info("create_endpoint API response", create_endpoint_api_response)
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully initiated {ENDPOINT_NAME} Endpoint creation')
    }
