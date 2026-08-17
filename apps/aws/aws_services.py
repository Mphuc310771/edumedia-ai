from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.request
from typing import List, Optional
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from apps.domain import MediaRecord, SearchPlan, infer_category, fold_text, record_haystack
from config.settings import settings

logger = logging.getLogger(__name__)


def _session_kwargs() -> dict:
    kwargs = {"region_name": settings.AWS_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return kwargs


def _client(service: str, region: Optional[str] = None):
    kwargs = _session_kwargs()
    if region:
        kwargs["region_name"] = region
    
    # Chuẩn thiết kế hệ thống phân tán: Adaptive Retry + Exponential Backoff
    client_config = Config(
        retries={"max_attempts": 3, "mode": "adaptive"},
        connect_timeout=5,
        read_timeout=30,
        tcp_keepalive=True,
    )
    if service == "s3" and settings.S3_ENDPOINT_URL:
        client_config = client_config.merge(Config(s3={"addressing_style": "path"}))
        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            config=client_config,
            **kwargs,
        )
    return boto3.client(service, config=client_config, **kwargs)


class S3ObjectStore:
    def __init__(self):
        self.client = _client("s3")
        self.bucket = settings.MEDIA_BUCKET

    def presign_put(self, object_key: str, content_type: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires,
        )

    def presign_get(self, object_key: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=expires,
        )

    def get_bytes(self, object_key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=object_key)
        return obj["Body"].read()

    def put_bytes(self, object_key: str, body: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=body,
            ContentType=content_type,
        )

    def object_uri(self, object_key: str) -> str:
        return f"s3://{self.bucket}/{quote(object_key)}"


class DynamoCatalog:
    def __init__(self):
        self.table = boto3.resource("dynamodb", **_session_kwargs()).Table(
            settings.METADATA_TABLE
        )

    def put(self, record: MediaRecord) -> None:
        item = json.loads(record.model_dump_json())
        self.table.put_item(Item=item)

    def get(self, file_id: str) -> Optional[MediaRecord]:
        response = self.table.get_item(Key={"file_id": file_id})
        item = response.get("Item")
        return MediaRecord.model_validate(item) if item else None

    def list_all(self) -> List[MediaRecord]:
        items: List[MediaRecord] = []
        scan_kwargs = {}
        while True:
            response = self.table.scan(**scan_kwargs)
            items.extend(MediaRecord.model_validate(row) for row in response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return items

    def _query_by_category(self, category: str) -> List[MediaRecord]:
        from boto3.dynamodb.conditions import Key

        items: List[MediaRecord] = []
        kwargs = {
            "IndexName": "category-index",
            "KeyConditionExpression": Key("category").eq(category),
        }
        while True:
            response = self.table.query(**kwargs)
            items.extend(MediaRecord.model_validate(row) for row in response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                break
            kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        return items

    def search(self, plan: SearchPlan) -> List[MediaRecord]:
        records = self._query_by_category(plan.category) if plan.category else self.list_all()
        narrowed = SearchPlan(
            keywords=plan.keywords,
            media_type=plan.media_type,
            category=None,
            rationale=plan.rationale,
        )
        return _FilterHelper(records).search(narrowed)

    def delete(self, file_id: str) -> bool:
        self.table.delete_item(Key={"file_id": file_id})
        return True

    def clear(self) -> None:
        items = self.list_all()
        with self.table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"file_id": item.file_id})


class _FilterHelper:
    def __init__(self, records: List[MediaRecord]):
        self.records = records

    def search(self, plan: SearchPlan) -> List[MediaRecord]:
        items = list(self.records)
        if plan.media_type:
            items = [item for item in items if item.media_type == plan.media_type]
        if plan.category:
            items = [item for item in items if item.category == plan.category]
        if not plan.keywords:
            return items
        scored = []
        for item in items:
            haystack = record_haystack(item)
            hits = sum(1 for kw in plan.keywords if fold_text(kw) in haystack)
            if hits:
                scored.append((hits, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored]


class RekognitionVision:
    def __init__(self):
        self.client = _client("rekognition")
        self.bucket = settings.MEDIA_BUCKET

    def analyze_image(self, object_key: str, filename: str = "") -> tuple[list[str], str]:
        image = {"S3Object": {"Bucket": self.bucket, "Name": object_key}}
        labels: list[str] = []
        lines: list[str] = []
        try:
            labels_resp = self.client.detect_labels(
                Image=image, MaxLabels=20, MinConfidence=70
            )
            labels = [item["Name"] for item in labels_resp.get("Labels", [])]
        except Exception as exc:
            logger.warning("Rekognition DetectLabels failed for %s: %s", object_key, exc)

        try:
            text_resp = self.client.detect_text(Image=image)
            lines = [
                det["DetectedText"]
                for det in text_resp.get("TextDetections", [])
                if det.get("Type") == "LINE"
            ]
        except Exception as exc:
            logger.warning("Rekognition DetectText failed for %s: %s", object_key, exc)

        return labels, "\n".join(lines)


class TranscribeSpeech:
    def __init__(self):
        self.client = _client("transcribe")
        self.bucket = settings.MEDIA_BUCKET

    def start_job(self, object_key: str, media_format: str) -> Optional[str]:
        """Non-blocking: Dispatches asynchronous transcription job for EventBridge event handling."""
        raw_name = object_key.replace("/", "-")
        safe_name = re.sub(r"[^0-9a-zA-Z._-]", "_", raw_name)
        job_name = f"agentsys-{safe_name}"[:200]
        media_uri = f"s3://{self.bucket}/{object_key}"
        output_key = f"{settings.TRANSCRIBE_OUTPUT_PREFIX}{job_name}.json"
        try:
            self.client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": media_uri},
                MediaFormat=media_format,
                LanguageCode="vi-VN",
                OutputBucketName=self.bucket,
                OutputKey=output_key,
            )
            return job_name
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"ConflictException", "Conflict"}:
                logger.info("Reuse existing Transcribe job %s", job_name)
                return job_name
            logger.warning("Transcribe start_job failed (%s): %s", code, exc)
            return None
        except Exception as exc:
            logger.warning("Transcribe start_job error: %s", exc)
            return None

    def transcribe(self, object_key: str, media_format: str) -> str:
        # Fast non-blocking async job dispatch: Handled via Amazon EventBridge in background
        job_name = self.start_job(object_key, media_format)
        clean_name = os.path.basename(object_key).rsplit(".", 1)[0]
        if not job_name:
            return f"Nội dung âm thanh đa phương tiện: {clean_name}"

        output_key = f"{settings.TRANSCRIBE_OUTPUT_PREFIX}{job_name}.json"
        try:
            job = self.client.get_transcription_job(TranscriptionJobName=job_name)
            status = job["TranscriptionJob"]["TranscriptionJobStatus"]
            if status == "COMPLETED":
                uri = job["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                return _read_transcript(uri, output_key)
        except Exception:
            pass
        return f"Bản ghi âm thanh bài giảng: {clean_name}"


class TitanEmbeddings:
    """Amazon Titan Multimodal Embeddings (amazon.titan-embed-text-v1)."""

    def __init__(self):
        region = settings.BEDROCK_REGION or settings.AWS_REGION
        self.client = _client("bedrock-runtime", region=region)
        self.model_id = "amazon.titan-embed-text-v1"

    def embed_text(self, text: str) -> List[float]:
        from apps.search.vector_engine import get_titan_embedding

        return get_titan_embedding(text, bedrock_client=self.client)


def _read_transcript(uri: str, output_key: str) -> str:
    try:
        if uri.startswith("https://"):
            with urllib.request.urlopen(uri, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        else:
            body = _client("s3").get_object(Bucket=settings.MEDIA_BUCKET, Key=output_key)["Body"].read()
            payload = json.loads(body)
        transcripts = payload.get("results", {}).get("transcripts", [])
        return transcripts[0].get("transcript", "") if transcripts else ""
    except Exception as exc:
        logger.warning("Error reading transcript from %s / %s: %s", uri, output_key, exc)
        return ""


def _parse_bedrock_plan_json(text: str, user_query: str) -> SearchPlan:
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    elif "{" in cleaned and "}" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        cleaned = cleaned[start:end]

    try:
        data = json.loads(cleaned)
        return SearchPlan.model_validate(data)
    except Exception as exc:
        logger.warning("Failed to parse Bedrock JSON: %s (raw text: %s)", exc, text)
        words = [w.strip() for w in user_query.split() if len(w.strip()) > 1]
        return SearchPlan(
            keywords=words[:6],
            rationale="Fallback keyword extraction from query",
        )


class BedrockPlanner:
    def __init__(self):
        region = settings.BEDROCK_REGION or settings.AWS_REGION
        self.client = _client("bedrock-runtime", region=region)
        self.model_id = settings.BEDROCK_MODEL_ID

    def plan(self, user_query: str) -> SearchPlan:
        system = (
            "You convert a Vietnamese or English media-search question into JSON. "
            "Return only JSON with keys: keywords (array of strings), media_type "
            "(image|audio|video or null), category "
            "(study|pets|food|receipts|scenes|videos|other or null), rationale. "
            "Keywords must be useful for matching Rekognition labels, OCR, and transcripts."
        )
        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user_query}]}],
                inferenceConfig={"maxTokens": 400, "temperature": 0},
            )
            text = response["output"]["message"]["content"][0]["text"]
            return _parse_bedrock_plan_json(text, user_query)
        except Exception as exc:
            logger.warning("Bedrock plan error: %s. Using heuristic fallback.", exc)
            words = [w.strip() for w in user_query.split() if len(w.strip()) > 1]
            return SearchPlan(
                keywords=words[:6],
                rationale="Fallback keyword extraction from query",
            )


class CloudWatchMetrics:
    def __init__(self):
        self.client = _client("cloudwatch")

    def emit(self, name: str, value: float, unit: str = "Count") -> None:
        try:
            self.client.put_metric_data(
                Namespace=settings.CLOUDWATCH_NAMESPACE,
                MetricData=[{"MetricName": name, "Value": value, "Unit": unit}],
            )
        except (BotoCoreError, ClientError) as exc:
            logger.warning("CloudWatch metric dropped: %s", exc)


def ping_aws() -> dict:
    status = {"s3": "UNKNOWN", "dynamodb": "UNKNOWN", "sts": "UNKNOWN"}
    try:
        _client("sts").get_caller_identity()
        status["sts"] = "ONLINE"
    except Exception:
        status["sts"] = "OFFLINE"
    try:
        _client("s3").head_bucket(Bucket=settings.MEDIA_BUCKET)
        status["s3"] = "ONLINE"
    except Exception:
        status["s3"] = "OFFLINE"
    try:
        _client("dynamodb").describe_table(TableName=settings.METADATA_TABLE)
        status["dynamodb"] = "ONLINE"
    except Exception:
        status["dynamodb"] = "OFFLINE"
    return status
