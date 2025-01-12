import json
import logging
import sys
import argparse
from datetime import datetime
from os import getenv
from pathlib import Path
from uuid import uuid4
from rich.logging import RichHandler
import handler

logger = logging.getLogger(__name__)
BUILD_ENV = getenv("BUILD_ENV", "development")
APP_NAME = getenv("APP_NAME", "trivialscan")
APP_ENV = getenv("APP_ENV", "Dev" if BUILD_ENV == "development" else "Prod")
AWS_ACCOUNT = getenv("AWS_ACCOUNT", "984310022655")
AWS_REGION = getenv("AWS_REGION", "ap-southeast-2")
PORT = None


def cli(target: str, port: int = 443, file_name: str = None):
    if "/" != target[0]:
        target = f"/{target}"
    if not file_name:
        file_name = f".{target}.json"

    now = datetime.utcnow()
    invoke_payload = Path(f".{BUILD_ENV}/invoke-payload.json")
    event = json.loads(invoke_payload.read_text(encoding="utf8"))
    rapidapi_token = handler.ssm_secret(
        f"/{APP_ENV}/Deploy/{APP_NAME}/rapidapi_token", WithDecryption=True
    )
    event["headers"].setdefault("x-rapidapi-proxy-secret", rapidapi_token)
    event["requestContext"]["accountId"] = AWS_ACCOUNT
    event["requestContext"]["http"]["path"] = target
    event["rawPath"] = target
    event["requestContext"]["time"] = now.strftime("%d/%b/%Y:%H:%M:%S %z")
    event["requestContext"]["timeEpoch"] = int(now.timestamp())
    if port:
        event["queryStringParameters"].setdefault("port", port)

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
    with open(file_name, "w", encoding="utf8") as handle:
        print(
            handler.lambda_handler(event, context).get("body"),
            file=handle,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "target",
        nargs="*",
        help="target host/domanin name to test. ~$ run.py google.com",
    )
    parser.add_argument(
        "-p",
        "--port",
        help="Optional: defaults to 443",
        dest="port",
        default=443,
    )
    parser.add_argument(
        "-O",
        "--json-file",
        help="Optional: defaults to {target}.json",
        dest="file_name",
        default=None,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v",
        "--errors-only",
        help="set logging level to ERROR (default CRITICAL)",
        dest="log_level_error",
        action="store_true",
    )
    group.add_argument(
        "-vv",
        "--warning",
        help="set logging level to WARNING (default CRITICAL)",
        dest="log_level_warning",
        action="store_true",
    )
    group.add_argument(
        "-vvv",
        "--info",
        help="set logging level to INFO (default CRITICAL)",
        dest="log_level_info",
        action="store_true",
    )
    group.add_argument(
        "-vvvv",
        "--debug",
        help="set logging level to DEBUG (default CRITICAL)",
        dest="log_level_debug",
        action="store_true",
    )
    LOG_LEVEL = logging.CRITICAL
    if parser.parse_args().log_level_error:
        LOG_LEVEL = logging.ERROR
    if parser.parse_args().log_level_warning:
        LOG_LEVEL = logging.WARNING
    if parser.parse_args().log_level_info:
        LOG_LEVEL = logging.INFO
    if parser.parse_args().log_level_debug:
        LOG_LEVEL = logging.DEBUG
    LOG_FORMAT = "%(asctime)s - %(name)s - [%(levelname)s] %(message)s"
    if sys.stdout.isatty():
        LOG_FORMAT = "%(message)s"
        logging.basicConfig(
            format=LOG_FORMAT,
            level=LOG_LEVEL,
            handlers=[RichHandler(rich_tracebacks=True)],
        )
    if not parser.parse_args().target:
        logger.error("no target provided")
        sys.exit(1)
    cli(
        target=parser.parse_args().target[0],
        port=int(parser.parse_args().port),
        file_name=parser.parse_args().file_name,
    )
