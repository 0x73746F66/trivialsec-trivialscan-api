import json
import logging
from datetime import datetime, timedelta
from os import getenv
import boto3
from botocore.exceptions import ClientError, ConnectionClosedError, ReadTimeoutError, ConnectTimeoutError, CapacityNotAvailableError
from retry.api import retry
import validators
import trivialscan

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.client('s3')

APP_ENV = getenv('APP_ENV', 'Dev')
APP_NAME = getenv('APP_NAME', 'trivialscan')

def object_exists(bucket_name :str, file_path :str, **kwargs):
    try:
        content = s3.head_object(Bucket=bucket_name, Key=file_path, **kwargs)
        return content.get('ResponseMetadata', None) is not None
    except ClientError:
        pass
    return False

@retry((ConnectionClosedError, ReadTimeoutError, ConnectTimeoutError, CapacityNotAvailableError), tries=3, delay=1.5, backoff=1)
def ssm_secret(parameter: str, default=None, **kwargs) -> str:
    logger.info(f"requesting secret {parameter}")
    try:
        ssm_client = boto3.client(service_name='ssm')
        response = ssm_client.get_parameter(
            Name=parameter, **kwargs
        )
        return default if not isinstance(response, dict) else response.get('Parameter', {}).get('Value', default)
    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.warning(f"The requested secret {parameter} was not found")
        elif err.response['Error']['Code'] == 'InvalidRequestException':
            logger.warning(f"The request was invalid due to: {err}")
        elif err.response['Error']['Code'] == 'InvalidParameterException':
            logger.warning(f"The request had invalid params: {err}")
    return default

def check_tls(domain_name :str, **kwargs) -> dict:
    evaluation_start = datetime.utcnow()
    _, results = trivialscan.analyse(host=domain_name, **kwargs)
    return trivialscan.to_dict(results, (datetime.utcnow() - evaluation_start).total_seconds())

def lambda_handler(event, context):
    rapidapi_user = event['headers'].get('x-rapidapi-user')
    rapidapi_subscription = event['headers'].get('x-rapidapi-subscription')
    rapidapi_version = event['headers'].get('x-rapidapi-version')
    ip_addr = event['headers'].get('x-forwarded-for')
    logger.info(f'"{rapidapi_user}","{rapidapi_subscription}","{rapidapi_version}","{ip_addr}"')
    rapidapi_proxy_secret = event['headers'].get('x-rapidapi-proxy-secret', 'default deny')
    rapidapi_token = ssm_secret(f'/{APP_ENV}/Deploy/{APP_NAME}/rapidapi_token', WithDecryption=True)
    if rapidapi_token != rapidapi_proxy_secret:
        logger.warning(f'x-rapidapi-token {rapidapi_token} {rapidapi_proxy_secret}')
        return {
            'statusCode': 403,
            'headers': {
                'WWW-Authenticate': 'Bearer realm="rapidapi" error="invalid_token"'
            }
        }
    path = event['rawPath'].split('/')
    if len(path) != 2:
        return {
            'statusCode': 422,
            'body': '{"msg": "Missing domain name"}'
        }
    domain_name = path[1]
    if validators.domain(domain_name) is not True:
        return {
            'statusCode': 422,
            'body': json.dumps({'msg': f"Invalid domain name [{domain_name}]"})
        }
    port = int(event['queryStringParameters'].get('port', 443))
    use_sni = bool(event['queryStringParameters'].get('use_sni', True))

    bucket_name = 'trivialscan-results'
    file_name = f"{hash(f'{domain_name}{port}{use_sni}')}.json"
    file_key = f'/domain/{domain_name}/{file_name}'
    logger.info(f'Reading {file_key} from {bucket_name}')
    if object_exists(bucket_name, file_key):
        obj = s3.get_object(Bucket=bucket_name, Key=file_key)
        stored_raw = obj.get('Body', '').read().strip()
        stored_data = json.loads(stored_raw)
        expire = datetime.utcnow() - timedelta(days=1)
        if isinstance(stored_data, dict) and stored_data.get('date'):
            last_checked = datetime.fromisoformat(stored_data.get('date'))
            if last_checked > expire:
                logger.info(f'HIT {domain_name}:{port}')
                return {
                    'statusCode': 200,
                    'body': stored_raw
                }

    logger.info(f'MISS {domain_name}:{port}')
    tls_data = check_tls(domain_name, port=port, use_sni=use_sni)
    json_data = json.dumps(tls_data, default=str, sort_keys=True)
    logger.info(f'Saving {file_key} to {bucket_name}')
    s3.put_object(Bucket=bucket_name, Key=file_key, Body=json_data)

    return {
        'statusCode': 200,
        'body': json_data
    }
