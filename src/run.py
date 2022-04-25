import json
import logging
import sys
from datetime import datetime
from os import getenv
from pathlib import Path
from uuid import uuid4

import handler

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] %(message)s", level=logging.INFO
)
BUILD_ENV = getenv("BUILD_ENV", "development")
APP_NAME = getenv("APP_NAME", "trivialscan")
APP_ENV = getenv("APP_ENV", "Dev")
AWS_ACCOUNT = getenv("AWS_ACCOUNT", "984310022655")
AWS_REGION = getenv("AWS_REGION", "ap-southeast-2")

PORT = None
TARGET = "/ssllabs.com"
if len(sys.argv) >= 2:
    TARGET = sys.argv[1]
if "/" != TARGET[0]:
    TARGET = f"/{TARGET}"
if ":" in TARGET:
    TARGET, PORT = TARGET.split(":")

now = datetime.utcnow()
invoke_payload = Path(f".{BUILD_ENV}/invoke-payload.json")
event = json.loads(invoke_payload.read_text(encoding="utf8"))
rapidapi_token = handler.ssm_secret(
    f"/{APP_ENV}/Deploy/{APP_NAME}/rapidapi_token", WithDecryption=True
)
event["headers"].setdefault("x-rapidapi-proxy-secret", rapidapi_token)
event["requestContext"]["accountId"] = AWS_ACCOUNT
event["requestContext"]["http"]["path"] = TARGET
event["rawPath"] = TARGET
event["requestContext"]["time"] = now.strftime("%d/%b/%Y:%H:%M:%S %z")
event["requestContext"]["timeEpoch"] = int(now.timestamp())
if PORT:
    event["queryStringParameters"].setdefault("port", PORT)

context = {
    "aws_request_id": uuid4(),
    "log_group_name": f"/aws/lambda/{APP_NAME}",
    "log_stream_name": f"{now.strftime('%Y/%m/%d')}/[$LATEST]efedd01b329b4041b660f9ce510228cc",
    "function_name": APP_NAME,
    "memory_limit_in_mb": 128,
    "function_version": "$LATEST",
    "invoked_function_arn": f"arn:aws:lambda:{AWS_REGION}:{AWS_ACCOUNT}:function:{APP_NAME}",
    "client_context": None,
    "identity": None,
}
logger.info(handler.lambda_handler(event, context))
