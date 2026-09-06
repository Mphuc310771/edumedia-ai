"""Capture redacted workshop evidence PNGs from live AWS + local UI.

Run from agent_sys/:  python scripts/capture_workshop_evidence.py
Does not print secrets. Account IDs / AKIA keys are blacked out in images.
"""
from __future__ import annotations

import json
import os
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "static" / "images" / "workshop"

ACCOUNT_RE = re.compile(r"\b\d{12}\b")
AKIA_RE = re.compile(r"AKIA[0-9A-Z]{16}")
KEY_RE = re.compile(r"(?i)(x-api-key|apikey|admin_api_key|aws_secret_access_key)\s*[:=]\s*\S+")


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def redact(text: str) -> str:
    text = ACCOUNT_RE.sub("************", text)
    text = AKIA_RE.sub("AKIA****************", text)
    text = KEY_RE.sub(r"\1=********", text)
    text = text.replace(os.environ.get("ADMIN_API_KEY", "___never___"), "********")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or ""
    if secret:
        text = text.replace(secret, "********")
    return text


def font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        ["consola.ttf", "consolab.ttf"]
        if mono
        else ["segoeui.ttf", "arial.ttf"]
    )
    windir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in names:
        path = windir / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def save_terminal(title: str, body: str, dest: Path, width: int = 1280, height: int = 720) -> None:
    img = Image.new("RGB", (width, height), "#0b1220")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, width, 48), fill="#111827")
    draw.ellipse((18, 16, 32, 30), fill="#f87171")
    draw.ellipse((40, 16, 54, 30), fill="#fbbf24")
    draw.ellipse((62, 16, 76, 30), fill="#34d399")
    draw.text((96, 12), title, fill="#e5e7eb", font=font(18))
    y = 64
    body_font = font(15, mono=True)
    for raw_line in redact(body).splitlines() or ["(empty)"]:
        for line in textwrap.wrap(raw_line, width=108) or [""]:
            if y > height - 28:
                break
            draw.text((24, y), line, fill="#d1d5db", font=body_font)
            y += 22
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")


def save_architecture(dest: Path) -> None:
    width, height = 1400, 820
    img = Image.new("RGB", (width, height), "#0b1220")
    draw = ImageDraw.Draw(img)
    title_f = font(28)
    box_f = font(16)
    small_f = font(14)
    draw.text((40, 24), "AgentSys — AWS serverless (lab, us-east-1)", fill="#f8fafc", font=title_f)
    draw.text(
        (40, 64),
        "Private S3 + SQS + Lambda + Rekognition/Transcribe + DynamoDB + Bedrock + CloudWatch",
        fill="#94a3b8",
        font=small_f,
    )

    def box(x, y, w, h, label, fill="#1e293b", outline="#8b5cf6"):
        draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=fill, outline=outline, width=2)
        tw = draw.textlength(label, font=box_f)
        draw.text((x + (w - tw) / 2, y + h / 2 - 10), label, fill="#f1f5f9", font=box_f)

    def arrow(x1, y1, x2, y2):
        draw.line((x1, y1, x2, y2), fill="#64748b", width=3)

    box(40, 140, 200, 70, "Browser / Vite :5174", fill="#312e81")
    box(320, 120, 220, 70, "HTTP API + API key")
    box(320, 230, 220, 70, "Lambda API")
    box(620, 120, 220, 70, "S3 private SSE-S3")
    box(620, 230, 220, 70, "SQS + DLQ")
    box(920, 180, 220, 70, "Lambda ingest")
    box(320, 370, 220, 70, "DynamoDB catalog")
    box(620, 370, 220, 70, "Bedrock Nova+Titan")
    box(920, 300, 220, 70, "Rekognition")
    box(920, 400, 220, 70, "Transcribe vi-VN")
    box(920, 500, 220, 70, "EventBridge")
    box(620, 530, 220, 70, "CloudWatch + alarms")

    arrow(240, 175, 320, 155)
    arrow(240, 175, 320, 265)
    arrow(240, 175, 620, 155)
    arrow(540, 155, 620, 155)
    arrow(540, 265, 620, 265)
    arrow(840, 155, 920, 215)
    arrow(840, 265, 920, 215)
    arrow(1030, 250, 1030, 300)
    arrow(1030, 370, 1030, 400)
    arrow(1030, 470, 1030, 500)
    arrow(920, 535, 840, 565)
    arrow(540, 405, 620, 405)
    arrow(430, 300, 430, 370)
    arrow(430, 440, 430, 500)
    draw.text((40, 740), "Account ID redacted in other evidence shots. Transcribe may be SubscriptionRequired.", fill="#64748b", font=small_f)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")


def aws_texts() -> dict[str, str]:
    import boto3
    from botocore.exceptions import ClientError

    region = os.environ.get("AWS_REGION", "us-east-1")
    session = boto3.Session(
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=region,
    )
    cfn = session.client("cloudformation")
    s3 = session.client("s3")
    ddb = session.client("dynamodb")
    logs = session.client("logs")
    cw = session.client("cloudwatch")

    stack = cfn.describe_stacks(StackName="agentsys")["Stacks"][0]
    outputs = {row["OutputKey"]: row["OutputValue"] for row in stack.get("Outputs") or []}
    bucket = outputs.get("MediaBucketName") or os.environ.get("MEDIA_BUCKET", "")
    sam_lines = [
        f"aws cloudformation describe-stacks --stack-name agentsys --region {region}",
        f"StackStatus: {stack.get('StackStatus')}",
        f"CreationTime: {stack.get('CreationTime')}",
        "Outputs:",
    ]
    for key, value in outputs.items():
        sam_lines.append(f"  {key}: {value}")

    s3_lines = [f"aws s3 ls s3://{bucket}/uploads/ --region {region}"]
    try:
        listed = s3.list_objects_v2(Bucket=bucket, Prefix="uploads/", MaxKeys=12)
        for obj in listed.get("Contents") or []:
            s3_lines.append(f"  {obj['LastModified']}  {obj['Size']:>10}  {obj['Key']}")
        if not listed.get("Contents"):
            s3_lines.append("  (bucket empty or prefix uploads/ missing)")
    except ClientError as exc:
        s3_lines.append(str(exc))

    ddb_lines = ["aws dynamodb scan --table-name AgentSysMediaMetadata --max-items 1"]
    try:
        scan = ddb.scan(TableName="AgentSysMediaMetadata", Limit=3)
        for item in scan.get("Items") or []:
            compact = {}
            for field in ("file_id", "filename", "status", "category", "subject", "ocr_text", "labels"):
                node = item.get(field)
                if not node:
                    continue
                if "S" in node:
                    compact[field] = node["S"][:180]
                elif "L" in node:
                    compact[field] = [el.get("S") for el in node["L"][:6]]
            ddb_lines.append(json.dumps(compact, ensure_ascii=False, indent=2))
            ddb_lines.append("---")
    except ClientError as exc:
        ddb_lines.append(str(exc))

    log_lines = ["aws logs tail /aws/lambda/agentsys-ingest --since 3h"]
    try:
        streams = logs.describe_log_streams(
            logGroupName="/aws/lambda/agentsys-ingest",
            orderBy="LastEventTime",
            descending=True,
            limit=1,
        )
        if streams.get("logStreams"):
            name = streams["logStreams"][0]["logStreamName"]
            events = logs.get_log_events(logGroupName="/aws/lambda/agentsys-ingest", logStreamName=name, limit=20)
            for event in events.get("events") or []:
                log_lines.append(event.get("message", "").rstrip())
        else:
            log_lines.append("(no ingest log streams yet — local ingest may not invoke this Lambda)")
    except ClientError as exc:
        log_lines.append(str(exc))

    alarm_lines = ["aws cloudwatch describe-alarms --alarm-name-prefix agentsys"]
    try:
        alarms = cw.describe_alarms(AlarmNamePrefix="agentsys")
        for alarm in alarms.get("MetricAlarms") or []:
            alarm_lines.append(
                f"{alarm.get('AlarmName')}: {alarm.get('StateValue')}  metric={alarm.get('MetricName')}  {alarm.get('ComparisonOperator')} {alarm.get('Threshold')}"
            )
        if not alarms.get("MetricAlarms"):
            alarm_lines.append("(no agentsys alarms found)")
    except ClientError as exc:
        alarm_lines.append(str(exc))

    return {
        "sam-deploy.png": ("CloudFormation stack agentsys", "\n".join(sam_lines)),
        "s3-uploads.png": ("S3 uploads/ prefix", "\n".join(s3_lines)),
        "rekognition.png": ("DynamoDB AgentSysMediaMetadata (labels + ocr_text)", "\n".join(ddb_lines)),
        "ingest-logs.png": ("CloudWatch Logs /aws/lambda/agentsys-ingest", "\n".join(log_lines)),
        "cloudwatch.png": ("CloudWatch alarms agentsys-*", "\n".join(alarm_lines)),
    }


def capture_ui() -> None:
    from playwright.sync_api import sync_playwright

    ui = OUT / "ui-upload.png"
    query = OUT / "bedrock-query.png"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:5174/", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(ui), full_page=False)
        box = page.locator("input[placeholder*='Gõ để lọc']")
        box.click()
        box.fill("tích phân đề thi cuối kỳ")
        box.press("Enter")
        page.wait_for_timeout(8000)
        page.screenshot(path=str(query), full_page=False)
        browser.close()


def main() -> None:
    load_dotenv()
    os.chdir(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    save_architecture(OUT / "architecture.png")
    print("wrote architecture.png")
    for name, (title, body) in aws_texts().items():
        save_terminal(title, body, OUT / name)
        print("wrote", name, (OUT / name).stat().st_size)
    capture_ui()
    print("wrote ui-upload.png", (OUT / "ui-upload.png").stat().st_size)
    print("wrote bedrock-query.png", (OUT / "bedrock-query.png").stat().st_size)


if __name__ == "__main__":
    main()
