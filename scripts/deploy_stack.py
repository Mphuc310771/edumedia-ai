"""Build and deploy the agentsys SAM stack. Reads ApiKey from .env; never prints it."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "infra" / "template.yaml"
PACK = ROOT / "pack"
SAMCONFIG = ROOT / "samconfig.toml"

LAMBDA_REQUIREMENTS = """\
fastapi>=0.115.0
mangum>=0.19.0
pydantic>=2.9.2
pydantic-settings>=2.5.2
boto3>=1.35.36
python-multipart>=0.0.12
slowapi>=0.1.9
anyio>=4.0.0
flashtext>=2.7
PyYAML>=6.0.1
Pillow>=10.0.0
"""


def _tool(name: str) -> str:
    found = shutil.which(name) or shutil.which(f"{name}.cmd")
    if not found:
        raise SystemExit(f"{name} not on PATH")
    return found


def _env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _admin_api_key() -> str:
    value = _env_value("ADMIN_API_KEY")
    if not value:
        raise SystemExit("ADMIN_API_KEY missing in .env")
    return value


def _alert_email() -> str:
    """Optional ALERT_EMAIL in .env -> AlertEmail parameter (SNS subscriber of the 7 alarms)."""
    return _env_value("ALERT_EMAIL")


def _frontend_origin_url() -> str:
    """Optional FRONTEND_ORIGIN_URL in .env -> FrontendOriginUrl parameter (CORS domain or *)."""
    return _env_value("FRONTEND_ORIGIN_URL") or "*"


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def _stage_pack() -> None:
    if PACK.exists():
        shutil.rmtree(PACK)
    PACK.mkdir()
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "tests")
    shutil.copytree(ROOT / "apps", PACK / "apps", ignore=ignore)
    shutil.copytree(ROOT / "config", PACK / "config", ignore=ignore)
    shutil.copytree(ROOT / "pipeline", PACK / "pipeline", ignore=ignore)
    (PACK / "requirements.txt").write_text(LAMBDA_REQUIREMENTS, encoding="utf-8")
    print("staged", PACK, "for SAM CodeUri")


def _write_samconfig(api_key: str, alert_email: str = "", frontend_origin: str = "*", bedrock_model: str = "us.amazon.nova-pro-v1:0") -> None:
    params = [f'    "ApiKey={api_key}",']
    if alert_email:
        params.append(f'    "AlertEmail={alert_email}",')
    if frontend_origin:
        params.append(f'    "FrontendOriginUrl={frontend_origin}",')
    if bedrock_model:
        params.append(f'    "BedrockModelId={bedrock_model}",')

    SAMCONFIG.write_text(
        "\n".join(
            [
                "version = 0.1",
                "[default.deploy.parameters]",
                'stack_name = "agentsys"',
                'region = "us-east-1"',
                'capabilities = "CAPABILITY_IAM"',
                "resolve_s3 = true",
                "confirm_changeset = false",
                "fail_on_empty_changeset = false",
                "parameter_overrides = [",
                *params,
                "]",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _patch_env_bucket(bucket: str) -> None:
    path = ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    found = False
    for line in lines:
        if line.startswith("MEDIA_BUCKET="):
            out.append(f"MEDIA_BUCKET={bucket}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"MEDIA_BUCKET={bucket}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _delete_failed_stack(aws: str) -> None:
    status = subprocess.run(
        [
            aws,
            "cloudformation",
            "describe-stacks",
            "--stack-name",
            "agentsys",
            "--region",
            "us-east-1",
            "--query",
            "Stacks[0].StackStatus",
            "--output",
            "text",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    current = (status.stdout or "").strip()
    if status.returncode != 0 or not current:
        print("no existing agentsys stack")
        return
    print("existing stack status", current)
    if current in {"ROLLBACK_COMPLETE", "ROLLBACK_FAILED", "CREATE_FAILED", "DELETE_FAILED"}:
        print("deleting failed stack agentsys")
        _run([aws, "cloudformation", "delete-stack", "--stack-name", "agentsys", "--region", "us-east-1"])
        _run([aws, "cloudformation", "wait", "stack-delete-complete", "--stack-name", "agentsys", "--region", "us-east-1"])


def main() -> None:
    api_key = _admin_api_key()
    alert_email = _alert_email()
    if not alert_email:
        print("ALERT_EMAIL not set in .env -> template default AlertEmail (placeholder) will be used")
    sam = _tool("sam")
    aws = _tool("aws")
    _stage_pack()
    _write_samconfig(api_key, alert_email, _frontend_origin_url())
    _delete_failed_stack(aws)
    _run([sam, "build", "--template-file", str(TEMPLATE)])
    _run(
        [
            sam,
            "deploy",
            "--template-file",
            str(ROOT / ".aws-sam" / "build" / "template.yaml"),
            "--config-file",
            str(SAMCONFIG),
        ]
    )
    query = subprocess.check_output(
        [
            aws,
            "cloudformation",
            "describe-stacks",
            "--stack-name",
            "agentsys",
            "--region",
            "us-east-1",
            "--query",
            "Stacks[0].Outputs",
            "--output",
            "json",
        ],
        cwd=ROOT,
        text=True,
    )
    import json

    outputs = {item["OutputKey"]: item["OutputValue"] for item in json.loads(query)}
    bucket = outputs.get("MediaBucketName", "")
    if bucket:
        _patch_env_bucket(bucket)
        print("MEDIA_BUCKET updated in .env")
    print("ApiEndpoint", outputs.get("ApiEndpoint", ""))
    print("MediaBucketName", bucket)
    print("MetadataTableName", outputs.get("MetadataTableName", ""))


if __name__ == "__main__":
    main()
