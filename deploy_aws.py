from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import truststore

truststore.inject_into_ssl()

import boto3
import botocore

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / ".deploy" / "lambda"
PACKAGE = BUILD / "package"
ARTIFACT = ROOT / ".deploy" / "memoryir-lambda.zip"
STACK_NAME = "memoryir-hackathon"
ROLE_NAME = "memoryir-hackathon-role"
FUNCTION_NAME = "memoryir-hackathon"
API_NAME = "memoryir-hackathon-http"
INLINE_POLICY_NAME = "memoryir-hackathon-execution"
DEFAULT_API_RATE_LIMIT = 1.0
DEFAULT_API_BURST_LIMIT = 5


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key.replace("_", "").isalnum() and (key[0].isalpha() or key[0] == "_"):
            os.environ.setdefault(key, value)


def require_env(keys: list[str]) -> None:
    missing = [key for key in keys if not os.environ.get(key)]
    if missing:
        raise SystemExit(f"Missing required env keys in creds.env: {', '.join(missing)}")


def run(cmd: list[str], *, cwd: Path = ROOT) -> None:
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def build_lambda_package() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    PACKAGE.mkdir(parents=True)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--platform",
            "manylinux2014_x86_64",
            "--implementation",
            "cp",
            "--python-version",
            "3.12",
            "--only-binary=:all:",
            "--target",
            str(PACKAGE),
            "-r",
            str(ROOT / "backend" / "requirements-lambda.txt"),
        ]
    )
    shutil.copytree(ROOT / "backend" / "app", PACKAGE / "app")
    shutil.copytree(ROOT / "backend" / "static", PACKAGE / "static")
    shutil.copytree(ROOT / "eval", PACKAGE / "eval", ignore=shutil.ignore_patterns("__pycache__"))
    if ARTIFACT.exists():
        ARTIFACT.unlink()
    with zipfile.ZipFile(ARTIFACT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in PACKAGE.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(PACKAGE))
    print(f"artifact={ARTIFACT} size_mb={ARTIFACT.stat().st_size / 1024 / 1024:.2f}")


def ensure_bucket(s3, bucket: str, region: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
        return
    except botocore.exceptions.ClientError:
        pass
    kwargs = {"Bucket": bucket}
    if region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**kwargs)
    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )


def put_runtime_parameters(ssm) -> None:
    ssm.put_parameter(
        Name="/memoryir/database-url",
        Value=os.environ["DATABASE_URL"],
        Type="SecureString",
        Overwrite=True,
    )
    ssm.put_parameter(
        Name="/memoryir/mcp-api-key",
        Value=os.environ["MCP_API_KEY"],
        Type="SecureString",
        Overwrite=True,
    )
    ssm.put_parameter(
        Name="/memoryir/mcp-cluster-id",
        Value=os.environ["MCP_CLUSTER_ID"],
        Type="String",
        Overwrite=True,
    )
    print("ssm_parameters=updated")


def packaged_template() -> str:
    return (ROOT / "template.yaml").read_text(encoding="utf-8")


def deploy_stack(cloudformation, template_body: str) -> None:
    kwargs = {
        "StackName": STACK_NAME,
        "TemplateBody": template_body,
        "Capabilities": ["CAPABILITY_NAMED_IAM"],
        "Parameters": [
            {
                "ParameterKey": "ArtifactBucket",
                "ParameterValue": os.environ["ARTIFACT_BUCKET"],
            },
            {
                "ParameterKey": "ArtifactKey",
                "ParameterValue": os.environ["ARTIFACT_KEY"],
            },
            {
                "ParameterKey": "DatabaseUrl",
                "ParameterValue": os.environ["DATABASE_URL"],
            },
            {
                "ParameterKey": "McpApiKey",
                "ParameterValue": os.environ["MCP_API_KEY"],
            },
            {
                "ParameterKey": "McpClusterId",
                "ParameterValue": os.environ["MCP_CLUSTER_ID"],
            },
        ],
    }
    try:
        stack = cloudformation.describe_stacks(StackName=STACK_NAME)["Stacks"][0]
        if stack["StackStatus"] == "ROLLBACK_COMPLETE":
            print("deleting_rollback_stack=memoryir-hackathon")
            cloudformation.delete_stack(StackName=STACK_NAME)
            cloudformation.get_waiter("stack_delete_complete").wait(
                StackName=STACK_NAME,
                WaiterConfig={"Delay": 10, "MaxAttempts": 60},
            )
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "ValidationError", "Message": "Stack does not exist"}},
                "DescribeStacks",
            )
        try:
            cloudformation.update_stack(**kwargs)
            waiter_name = "stack_update_complete"
        except botocore.exceptions.ClientError as exc:
            if "No updates are to be performed" in str(exc):
                print("stack=no_updates")
                return
            raise
    except botocore.exceptions.ClientError as exc:
        if "does not exist" not in str(exc):
            raise
        cloudformation.create_stack(**kwargs)
        waiter_name = "stack_create_complete"

    print(f"waiting_for={waiter_name}")
    waiter = cloudformation.get_waiter(waiter_name)
    waiter.wait(StackName=STACK_NAME, WaiterConfig={"Delay": 15, "MaxAttempts": 80})


def print_outputs(cloudformation) -> None:
    stacks = cloudformation.describe_stacks(StackName=STACK_NAME)["Stacks"]
    outputs = {item["OutputKey"]: item["OutputValue"] for item in stacks[0].get("Outputs", [])}
    if outputs.get("MemoryIRUrl"):
        print(f"MemoryIRUrl={outputs['MemoryIRUrl']}")


def lambda_env(region: str) -> dict[str, str]:
    return {
        "DATABASE_URL": os.environ["DATABASE_URL"],
        "MCP_API_KEY": os.environ["MCP_API_KEY"],
        "MCP_CLUSTER_ID": os.environ["MCP_CLUSTER_ID"],
        "MEMORYIR_PROVIDER": os.environ.get("MEMORYIR_PROVIDER", "bedrock"),
        "BEDROCK_AGENT_MODEL_ID": os.environ.get(
            "BEDROCK_AGENT_MODEL_ID", "amazon.nova-micro-v1:0"
        ),
        "BEDROCK_EMBED_MODEL_ID": os.environ.get(
            "BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0"
        ),
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
    }


def api_throttle_settings() -> dict[str, float | int]:
    return {
        "ThrottlingRateLimit": float(
            os.environ.get("MEMORYIR_API_RATE_LIMIT", DEFAULT_API_RATE_LIMIT)
        ),
        "ThrottlingBurstLimit": int(
            os.environ.get("MEMORYIR_API_BURST_LIMIT", DEFAULT_API_BURST_LIMIT)
        ),
    }


def ensure_execution_role(iam, region: str, account_id: str) -> str:
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    try:
        role = iam.get_role(RoleName=ROLE_NAME)["Role"]
    except iam.exceptions.NoSuchEntityException:
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="MemoryIR hackathon Lambda execution role",
        )["Role"]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": f"arn:aws:logs:{region}:{account_id}:*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Converse",
                    "bedrock:ConverseStream",
                ],
                "Resource": "*",
            },
        ],
    }
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName=INLINE_POLICY_NAME,
        PolicyDocument=json.dumps(policy),
    )
    print(f"role={role['Arn']}")
    return role["Arn"]


def wait_for_role_propagation(lambda_client, role_arn: str) -> None:
    # IAM role propagation is eventually consistent and Lambda create calls are picky.
    lambda_client.get_account_settings()
    print(f"role_propagation_wait=10s role={role_arn}")
    time.sleep(10)


def lambda_exists(lambda_client) -> bool:
    try:
        lambda_client.get_function(FunctionName=FUNCTION_NAME)
        return True
    except lambda_client.exceptions.ResourceNotFoundException:
        return False


def wait_lambda_updated(lambda_client) -> None:
    lambda_client.get_waiter("function_updated").wait(
        FunctionName=FUNCTION_NAME,
        WaiterConfig={"Delay": 5, "MaxAttempts": 60},
    )


def create_or_update_lambda(lambda_client, role_arn: str, bucket: str, key: str, region: str) -> str:
    env = {"Variables": lambda_env(region)}
    if lambda_exists(lambda_client):
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Runtime="python3.12",
            Role=role_arn,
            Handler="app.main.handler",
            Timeout=45,
            MemorySize=1024,
            Environment=env,
        )
        wait_lambda_updated(lambda_client)
        lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            S3Bucket=bucket,
            S3Key=key,
            Publish=True,
        )
        wait_lambda_updated(lambda_client)
        print("lambda=updated")
    else:
        lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime="python3.12",
            Role=role_arn,
            Handler="app.main.handler",
            Code={"S3Bucket": bucket, "S3Key": key},
            Timeout=45,
            MemorySize=1024,
            Environment=env,
            PackageType="Zip",
            Publish=True,
        )
        lambda_client.get_waiter("function_active").wait(
            FunctionName=FUNCTION_NAME,
            WaiterConfig={"Delay": 5, "MaxAttempts": 60},
        )
        print("lambda=created")

    try:
        lambda_client.put_function_concurrency(
            FunctionName=FUNCTION_NAME,
            ReservedConcurrentExecutions=3,
        )
        print("reserved_concurrency=3")
    except botocore.exceptions.ClientError as exc:
        print(f"reserved_concurrency=skipped reason={exc.response['Error'].get('Code')}")

    return lambda_client.get_function_configuration(FunctionName=FUNCTION_NAME)["FunctionArn"]


def find_api(apigateway) -> dict | None:
    paginator = apigateway.get_paginator("get_apis")
    for page in paginator.paginate():
        for item in page.get("Items", []):
            if item.get("Name") == API_NAME:
                return item
    return None


def find_item_by_key(apigateway, method: str, api_id: str, key: str, value: str) -> dict | None:
    paginator = apigateway.get_paginator(method)
    for page in paginator.paginate(ApiId=api_id):
        for item in page.get("Items", []):
            if item.get(key) == value:
                return item
    return None


def ensure_http_api(apigateway, lambda_client, function_arn: str, region: str, account_id: str) -> str:
    throttle_settings = api_throttle_settings()
    api = find_api(apigateway)
    if api:
        api_id = api["ApiId"]
        endpoint = api["ApiEndpoint"]
        print(f"http_api=reused id={api_id}")
    else:
        api = apigateway.create_api(Name=API_NAME, ProtocolType="HTTP")
        api_id = api["ApiId"]
        endpoint = api["ApiEndpoint"]
        print(f"http_api=created id={api_id}")

    integration = find_item_by_key(
        apigateway,
        "get_integrations",
        api_id,
        "IntegrationUri",
        function_arn,
    )
    if integration:
        integration_id = integration["IntegrationId"]
    else:
        integration = apigateway.create_integration(
            ApiId=api_id,
            IntegrationType="AWS_PROXY",
            IntegrationMethod="POST",
            IntegrationUri=function_arn,
            PayloadFormatVersion="2.0",
        )
        integration_id = integration["IntegrationId"]

    route = find_item_by_key(apigateway, "get_routes", api_id, "RouteKey", "$default")
    target = f"integrations/{integration_id}"
    if route:
        if route.get("Target") != target:
            apigateway.update_route(ApiId=api_id, RouteId=route["RouteId"], Target=target)
    else:
        apigateway.create_route(ApiId=api_id, RouteKey="$default", Target=target)

    stage = find_item_by_key(apigateway, "get_stages", api_id, "StageName", "$default")
    if stage:
        apigateway.update_stage(
            ApiId=api_id,
            StageName="$default",
            AutoDeploy=True,
            DefaultRouteSettings=throttle_settings,
        )
    else:
        apigateway.create_stage(
            ApiId=api_id,
            StageName="$default",
            AutoDeploy=True,
            DefaultRouteSettings=throttle_settings,
        )
    print(
        "request_gating=api_gateway_throttle "
        f"rate_per_second={throttle_settings['ThrottlingRateLimit']} "
        f"burst={throttle_settings['ThrottlingBurstLimit']}"
    )

    statement_id = f"memoryir-hackathon-httpapi-{api_id}"
    source_arn = f"arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*"
    try:
        lambda_client.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId=statement_id,
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=source_arn,
        )
    except lambda_client.exceptions.ResourceConflictException:
        pass

    url = endpoint.rstrip("/") + "/"
    print(f"MemoryIRUrl={url}")
    return url


def deploy_direct(session, bucket: str, key: str, region: str, account_id: str) -> None:
    iam = session.client("iam")
    lambda_client = session.client("lambda")
    apigateway = session.client("apigatewayv2")

    role_arn = ensure_execution_role(iam, region, account_id)
    wait_for_role_propagation(lambda_client, role_arn)
    function_arn = create_or_update_lambda(lambda_client, role_arn, bucket, key, region)
    ensure_http_api(apigateway, lambda_client, function_arn, region, account_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy MemoryIR without requiring aws/sam CLIs.")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Create/update Lambda and HTTP API directly instead of using CloudFormation.",
    )
    args = parser.parse_args()

    load_env(ROOT / "creds.env")
    require_env(["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "DATABASE_URL", "MCP_API_KEY", "MCP_CLUSTER_ID"])
    region = os.environ["AWS_REGION"]

    session = boto3.Session(region_name=region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    bucket = f"memoryir-hackathon-artifacts-{account_id}-{region}".lower()
    key = f"lambda/memoryir-{int(time.time())}.zip"

    if not args.skip_build:
        build_lambda_package()

    s3 = session.client("s3")
    cloudformation = session.client("cloudformation")

    ensure_bucket(s3, bucket, region)
    s3.upload_file(str(ARTIFACT), bucket, key, ExtraArgs={"ServerSideEncryption": "AES256"})
    print("artifact_uploaded=ok")
    os.environ["ARTIFACT_BUCKET"] = bucket
    os.environ["ARTIFACT_KEY"] = key
    if args.direct:
        deploy_direct(session, bucket, key, region, account_id)
    else:
        deploy_stack(cloudformation, packaged_template())
        print_outputs(cloudformation)


if __name__ == "__main__":
    main()
