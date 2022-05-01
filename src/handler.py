import json
import logging
from datetime import datetime, timedelta
from os import getenv
from tlstrust import TrustStore
import boto3
import trivialscan
import validators
from botocore.exceptions import (
    CapacityNotAvailableError,
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    ReadTimeoutError,
)
from retry.api import retry

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.client("s3")

APP_ENV = getenv("APP_ENV", "Dev")
APP_NAME = getenv("APP_NAME", "trivialscan")
DISABLE_CACHE = bool(getenv("DISABLE_CACHE"))


def object_exists(bucket_name: str, file_path: str, **kwargs):
    try:
        content = s3.head_object(Bucket=bucket_name, Key=file_path, **kwargs)
        return content.get("ResponseMetadata", None) is not None
    except ClientError:
        pass
    return False


@retry(
    (
        ConnectionClosedError,
        ReadTimeoutError,
        ConnectTimeoutError,
        CapacityNotAvailableError,
    ),
    tries=3,
    delay=1.5,
    backoff=1,
)
def ssm_secret(parameter: str, default=None, **kwargs) -> str:
    logger.info(f"requesting secret {parameter}")
    try:
        ssm_client = boto3.client(service_name="ssm")
        response = ssm_client.get_parameter(Name=parameter, **kwargs)
        return (
            default
            if not isinstance(response, dict)
            else response.get("Parameter", {}).get("Value", default)
        )
    except ClientError as err:
        if err.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.warning(f"The requested secret {parameter} was not found")
        elif err.response["Error"]["Code"] == "InvalidRequestException":
            logger.warning(f"The request was invalid due to: {err}")
        elif err.response["Error"]["Code"] == "InvalidParameterException":
            logger.warning(f"The request had invalid params: {err}")
    return default


def check_tls(domain_name: str, **kwargs) -> dict:
    evaluation_start = datetime.utcnow()
    _, results = trivialscan.analyse(host=domain_name, **kwargs)
    data = trivialscan.to_dict(
        results, (datetime.utcnow() - evaluation_start).total_seconds()
    )
    results = []
    for validation in data["validations"]:
        logger.info(validation["certificate_type"])
        if validation["certificate_type"] == "Root CA":
            trust_store = TrustStore(
                validation["certificate_subject_key_identifier"]
                if not validation.get("certification_authority_authorization")
                else validation["certification_authority_authorization"]
            )
            validation["certificate_trust"] = trust_store.to_dict()
        results.append(validation)
    data["validations"] = results
    return data


def lambda_handler(event, context):  # pylint: disable=unused-argument
    evaluation_start = datetime.utcnow()
    rapidapi_user = event["headers"].get("x-rapidapi-user")
    rapidapi_subscription = event["headers"].get("x-rapidapi-subscription")
    rapidapi_version = event["headers"].get("x-rapidapi-version")
    ip_addr = event["headers"].get("x-forwarded-for")
    logger.info(
        f'"{rapidapi_user}","{rapidapi_subscription}","{rapidapi_version}","{ip_addr}"'
    )
    rapidapi_proxy_secret = event["headers"].get(
        "x-rapidapi-proxy-secret", "default deny"
    )
    rapidapi_token = ssm_secret(
        f"/{APP_ENV}/Deploy/{APP_NAME}/rapidapi_token", WithDecryption=True
    )
    if rapidapi_token != rapidapi_proxy_secret:
        logger.warning(f"x-rapidapi-token {rapidapi_token} {rapidapi_proxy_secret}")
        return {
            "statusCode": 403,
            "headers": {
                "WWW-Authenticate": 'Bearer realm="rapidapi" error="invalid_token"'
            },
        }
    path = event["rawPath"].split("/")
    if len(path) != 2:
        return {"statusCode": 422, "body": '{"msg": "Missing domain name"}'}
    domain_name = path[1]
    if validators.domain(domain_name) is not True:
        return {
            "statusCode": 422,
            "body": json.dumps({"msg": f"Invalid domain name {domain_name}"}),
        }
    port = int(event["queryStringParameters"].get("port", 443))
    use_sni = bool(event["queryStringParameters"].get("use_sni", True))
    file_name = evaluation_start.strftime("%Y/%b/%d")
    bucket_name = "trivialscan-results"
    file_key = f"domains/{domain_name}/{port}/{file_name}.json"
    logger.info(f"Reading {file_key} from {bucket_name}")
    json_data = None
    tls_data = None
    logger.info(APP_ENV)
    if not DISABLE_CACHE and object_exists(bucket_name, file_key):
        obj = s3.get_object(Bucket=bucket_name, Key=file_key)
        stored_raw = obj.get("Body", "").read().strip()
        stored_data = json.loads(stored_raw)
        expire = evaluation_start - timedelta(days=1)
        if isinstance(stored_data, dict) and stored_data.get("date"):
            last_checked = datetime.fromisoformat(stored_data.get("date"))
            if last_checked > expire:
                logger.info(f"HIT {domain_name}:{port}")
                stored_data["evaluation_api_processing"] = (
                    datetime.utcnow() - evaluation_start
                ).total_seconds()
                tls_data = stored_data
                json_data = json.dumps(tls_data, default=str, sort_keys=True)

    if not json_data:
        logger.info(f"MISS {domain_name}:{port}")
        tls_data = check_tls(domain_name, port=port, use_sni=use_sni)
        tls_data["evaluation_api_processing"] = (
            datetime.utcnow() - evaluation_start
        ).total_seconds()
        json_data = json.dumps(tls_data, default=str, sort_keys=True)
        logger.info(f"Saving {file_key} to {bucket_name}")
        s3.put_object(Bucket=bucket_name, Key=file_key, Body=json_data)

    return {"statusCode": 200, "body": json_data}
