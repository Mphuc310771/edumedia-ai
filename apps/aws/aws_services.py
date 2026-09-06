from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.request
from decimal import Decimal
from typing import List, Optional
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from apps.domain import MediaRecord, SearchPlan, infer_category, fold_text, matches_subject_filter, record_haystack
from config.settings import settings

logger = logging.getLogger(__name__)

# Converse daily token cap vs short rate-limit cooldowns.
_BEDROCK_SKIP_UNTIL = 0.0
_BEDROCK_RATE_SKIP_UNTIL = 0.0
_BEDROCK_QUOTA_COOLDOWN_SECONDS = 6 * 3600
_BEDROCK_RATE_COOLDOWN_SECONDS = 45


def _heuristic_search_plan(user_query: str, rationale: str) -> SearchPlan:
    from apps.domain import infer_subject

    words = [w.strip() for w in re.findall(r"[\wÀ-ỹ]+", user_query) if len(w.strip()) > 1]
    subject = infer_subject([], user_query, "", "")
    return SearchPlan(
        keywords=words[:8],
        subject=None if subject == "none" else subject,
        category="study" if subject not in {"none", None} else None,
        rationale=rationale,
        planner_source="heuristic",
    )


def _exc_blob(exc: BaseException) -> str:
    code = ""
    message = str(exc)
    if isinstance(exc, ClientError):
        err = exc.response.get("Error", {})
        code = str(err.get("Code", ""))
        message = str(err.get("Message", message))
    return f"{code} {message}".lower()


def _is_daily_token_throttle(exc: BaseException) -> bool:
    blob = _exc_blob(exc)
    return "too many tokens" in blob or "tokens per day" in blob


def _is_rate_throttle(exc: BaseException) -> bool:
    blob = _exc_blob(exc)
    if _is_daily_token_throttle(exc):
        return False
    return "throttling" in blob or "too many requests" in blob


def _bedrock_quota_blocked() -> bool:
    return time.time() < _BEDROCK_SKIP_UNTIL


def _bedrock_rate_blocked() -> bool:
    return time.time() < _BEDROCK_RATE_SKIP_UNTIL


def _mark_bedrock_daily_quota() -> None:
    global _BEDROCK_SKIP_UNTIL
    _BEDROCK_SKIP_UNTIL = time.time() + _BEDROCK_QUOTA_COOLDOWN_SECONDS
    logger.warning(
        "Bedrock daily token cap hit. Skip Converse for %s hours; search uses keywords until then.",
        _BEDROCK_QUOTA_COOLDOWN_SECONDS // 3600,
    )


def _mark_bedrock_rate_limit() -> None:
    global _BEDROCK_RATE_SKIP_UNTIL
    _BEDROCK_RATE_SKIP_UNTIL = time.time() + _BEDROCK_RATE_COOLDOWN_SECONDS
    logger.warning("Bedrock rate limit. Skip Converse for %ss.", _BEDROCK_RATE_COOLDOWN_SECONDS)


def _session_kwargs() -> dict:
    kwargs = {"region_name": settings.AWS_REGION}
    # When running on AWS Lambda, always use Lambda's IAM execution role
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
            if settings.AWS_SESSION_TOKEN:
                kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
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
    if service == "bedrock-runtime":
        client_config = Config(
            retries={"max_attempts": 1, "mode": "standard"},
            connect_timeout=5,
            read_timeout=30,
            tcp_keepalive=True,
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
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return obj["Body"].read()
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NoSuchBucket"):
                return b""
            raise

    def put_bytes(self, object_key: str, body: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=body,
            ContentType=content_type,
        )

    def object_uri(self, object_key: str) -> str:
        return f"s3://{self.bucket}/{quote(object_key)}"

    def delete_object(self, object_key: str) -> None:
        if not object_key:
            return
        self.client.delete_object(Bucket=self.bucket, Key=object_key)


class DynamoCatalog:
    def __init__(self):
        self.table = boto3.resource("dynamodb", **_session_kwargs()).Table(
            settings.METADATA_TABLE
        )

    def put(self, record: MediaRecord) -> None:
        item = json.loads(record.model_dump_json(), parse_float=Decimal)
        item = {key: value for key, value in item.items() if value is not None}
        self.table.put_item(Item=item)

    def get(self, file_id: str) -> Optional[MediaRecord]:
        response = self.table.get_item(Key={"file_id": file_id})
        item = response.get("Item")
        if not item:
            return None
        try:
            return MediaRecord.model_validate(item)
        except Exception as exc:
            logger.warning("Could not validate MediaRecord for file_id=%s: %s", file_id, exc)
            return None

    def list_all(self) -> List[MediaRecord]:
        items: List[MediaRecord] = []
        scan_kwargs = {}
        while True:
            response = self.table.scan(**scan_kwargs)
            for row in response.get("Items", []):
                file_id = str(row.get("file_id", ""))
                if "#CHUNK#" in file_id or "parent_file_id" in row:
                    continue
                try:
                    items.append(MediaRecord.model_validate(row))
                except Exception:
                    continue
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
            subject=plan.subject,
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
        if plan.subject:
            items = [item for item in items if matches_subject_filter(item, plan.subject)]
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

    def _rekognition_image(self, object_key: str, filename: str = "", *, as_jpeg: bool = False) -> dict:
        from apps.aws.image_convert import image_bytes_to_jpeg, needs_rekognition_convert

        if as_jpeg or needs_rekognition_convert(filename or object_key):
            raw = S3ObjectStore().get_bytes(object_key)
            return {"Bytes": image_bytes_to_jpeg(raw)}
        return {"S3Object": {"Bucket": self.bucket, "Name": object_key}}

    @staticmethod
    def _unsupported_format(exc: Exception) -> bool:
        if isinstance(exc, ClientError):
            code = exc.response.get("Error", {}).get("Code", "")
            if "InvalidImageFormat" in code:
                return True
        return "InvalidImageFormat" in str(exc)

    def analyze_image(self, object_key: str, filename: str = "") -> tuple[list[str], str]:
        image = self._rekognition_image(object_key, filename)
        labels: list[str] = []
        lines: list[str] = []
        labels_error: Exception | None = None
        text_error: Exception | None = None
        try:
            labels_resp = self.client.detect_labels(
                Image=image, MaxLabels=20, MinConfidence=70
            )
            labels = [item["Name"] for item in labels_resp.get("Labels", [])]
        except Exception as exc:
            if self._unsupported_format(exc) and "Bytes" not in image:
                logger.info("Rekognition format retry as JPEG for %s", object_key)
                return self.analyze_image(object_key, filename="retry.webp")
            labels_error = exc
            logger.warning("Rekognition DetectLabels failed for %s: %s", object_key, exc)

        try:
            text_resp = self.client.detect_text(Image=image)
            lines = [
                det["DetectedText"]
                for det in text_resp.get("TextDetections", [])
                if det.get("Type") == "LINE"
            ]
        except Exception as exc:
            if self._unsupported_format(exc) and "Bytes" not in image and labels_error is None:
                logger.info("Rekognition OCR format retry as JPEG for %s", object_key)
                return self.analyze_image(object_key, filename="retry.webp")
            text_error = exc
            logger.warning("Rekognition DetectText failed for %s: %s", object_key, exc)

        if labels_error and text_error:
            raise RuntimeError(
                "Amazon Rekognition không đọc được định dạng ảnh này "
                f"(cần JPEG/PNG; WebP sẽ được chuyển tự động). Chi tiết: {labels_error}"
            )
        return labels, "\n".join(lines)


class TranscribeSpeech:
    def __init__(self):
        self.client = _client("transcribe")
        self.bucket = settings.MEDIA_BUCKET

    def start_job(self, object_key: str, media_format: str, file_id: str = "") -> Optional[str]:
        """Non-blocking: Dispatches asynchronous transcription job for EventBridge event handling."""
        raw_name = object_key.replace("/", "-")
        safe_name = re.sub(r"[^0-9a-zA-Z._-]", "_", raw_name)
        safe_fid = re.sub(r"[^0-9a-zA-Z._-]", "_", file_id) if file_id else ""
        # Encode file_id in job name so EventBridge callback can GetItem instead of Scan.
        if safe_fid:
            job_name = f"agentsys--{safe_fid}--{safe_name}"[:200]
        else:
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

    def read_job_transcript(self, job_name: str) -> str:
        job = self.client.get_transcription_job(TranscriptionJobName=job_name)
        status = job["TranscriptionJob"]["TranscriptionJobStatus"]
        if status != "COMPLETED":
            return ""
        uri = job["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        output_key = f"{settings.TRANSCRIBE_OUTPUT_PREFIX}{job_name}.json"
        return _read_transcript(uri, output_key)

    def wait_for_job(self, job_name: str) -> str:
        deadline = time.time() + settings.TRANSCRIBE_MAX_WAIT_SECONDS
        last_status = "UNKNOWN"
        while time.time() < deadline:
            job = self.client.get_transcription_job(TranscriptionJobName=job_name)
            last_status = job["TranscriptionJob"]["TranscriptionJobStatus"]
            if last_status == "COMPLETED":
                return self.read_job_transcript(job_name)
            if last_status == "FAILED":
                reason = job["TranscriptionJob"].get("FailureReason", "failed")
                raise RuntimeError(f"Amazon Transcribe failed: {reason}")
            time.sleep(settings.TRANSCRIBE_POLL_SECONDS)
        raise TimeoutError(
            f"Amazon Transcribe job {job_name} still {last_status} after {settings.TRANSCRIBE_MAX_WAIT_SECONDS}s"
        )

    def transcribe(self, object_key: str, media_format: str, file_id: str = "") -> str:
        job_name = self.start_job(object_key, media_format, file_id=file_id)
        if not job_name:
            raise RuntimeError("Amazon Transcribe did not start a job")
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return ""
        return self.wait_for_job(job_name)


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
    # 1. Try reading directly from S3 (customer bucket / private S3)
    if output_key and settings.MEDIA_BUCKET:
        try:
            body = _client("s3").get_object(Bucket=settings.MEDIA_BUCKET, Key=output_key)["Body"].read()
            payload = json.loads(body.decode("utf-8"))
            transcripts = payload.get("results", {}).get("transcripts", [])
            if transcripts and transcripts[0].get("transcript"):
                return transcripts[0].get("transcript", "").strip()
        except Exception as s3_exc:
            logger.debug("Could not read transcript directly from S3 (%s): %s", output_key, s3_exc)

    # 2. Fallback to HTTPS URL (AWS-managed bucket with presigned link)
    if uri and uri.startswith("https://"):
        try:
            with urllib.request.urlopen(uri, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
                transcripts = payload.get("results", {}).get("transcripts", [])
                if transcripts and transcripts[0].get("transcript"):
                    return transcripts[0].get("transcript", "").strip()
        except Exception as http_exc:
            logger.warning("Could not read transcript from URL (%s): %s", uri, http_exc)

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
        if "search_plan" in data and isinstance(data["search_plan"], dict):
            plan_dict = dict(data["search_plan"])
            rag = data.get("rag_answer", {})
            if isinstance(rag, dict):
                plan_dict["direct_answer"] = rag.get("direct_answer")
                plan_dict["evidence_snippet"] = rag.get("evidence_snippet")
                plan_dict["source_file"] = rag.get("source_file")
            plan = SearchPlan.model_validate(plan_dict)
        else:
            plan = SearchPlan.model_validate(data)
        plan.planner_source = "bedrock"
        return plan
    except Exception as exc:
        logger.warning("Failed to parse Bedrock JSON: %s (raw text: %s)", exc, text)
        return _heuristic_search_plan(user_query, "Bedrock unavailable — keyword fallback")


_PLAN_CACHE: dict[str, tuple[float, SearchPlan]] = {}
_PLAN_CACHE_TTL_SECONDS = 3600.0  # 1 hour cache
_PLAN_CACHE_MAX_SIZE = 256


class BedrockPlanner:
    def __init__(self):
        region = settings.BEDROCK_REGION or settings.AWS_REGION
        self.client = _client("bedrock-runtime", region=region)
        self.model_id = settings.BEDROCK_MODEL_ID

    def plan(self, user_query: str) -> SearchPlan:
        cache_key = " ".join(user_query.strip().lower().split())
        now = time.time()
        if cache_key and cache_key in _PLAN_CACHE:
            cached_at, cached_plan = _PLAN_CACHE[cache_key]
            if now - cached_at < _PLAN_CACHE_TTL_SECONDS:
                logger.debug("Bedrock plan cache hit for query=%r", user_query)
                return cached_plan.model_copy(deep=True)

        if _bedrock_quota_blocked():
            return _heuristic_search_plan(
                user_query,
                "Bedrock hết hạn mức token trong ngày — đang tìm theo từ khóa. Thử lại sau vài giờ hoặc ngày mai.",
            )
        if _bedrock_rate_blocked():
            return _heuristic_search_plan(
                user_query,
                "Bedrock đang bị giới hạn tốc độ — tìm theo từ khóa trong khoảng 1 phút.",
            )
        system = (
            "You are the Intelligent Query Planner and Keyword Enrichment Engine for AgentSys, a Serverless Multimodal Search System on AWS.\n"
            "Your task is to analyze user search queries in Vietnamese or English and generate an enriched JSON search plan.\n\n"
            "CRITICAL OUTPUT REQUIREMENT:\n"
            "Return ONLY a single valid JSON object matching the schema below. Do NOT wrap in markdown, backticks (```), or add any explanations outside the JSON.\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            '  "keywords": ["list", "of", "expanded", "synonyms", "in", "Vietnamese", "and", "English"],\n'
            '  "media_type": "image" | "audio" | "video" | null,\n'
            '  "category": "study" | "pets" | "food" | "receipts" | "scenes" | "videos" | "other" | null,\n'
            '  "subject": "math" | "os" | "networks" | "programming" | "database" | "cloud" | "lecture" | "english" | "physics" | "chemistry" | "biology" | "economics" | "law" | "philosophy" | "pe" | "off_major" | null,\n'
            '  "rationale": "Brief rationale in Vietnamese explaining the chosen filters and keyword expansion."\n'
            "}\n\n"
            "RULES FOR KEYWORD ENRICHMENT & MODALITY INFERENCE:\n"
            "1. Infer media_type from natural language cues:\n"
            '   - "nghe", "thầy dặn", "ghi âm", "tiếng", "giọng", "audio", "bài giảng nói" -> media_type: "audio"\n'
            '   - "ảnh", "chụp", "bảng", "slide", "hóa đơn", "chó", "mèo", "photo", "picture" -> media_type: "image"\n'
            '   - "video", "clip", "quay", "thuyết trình", "ghi hình" -> media_type: "video"\n'
            "   - If not specified, leave media_type as null.\n"
            '2. Enrich "keywords" with synonyms, academic context, and English equivalents to match both Amazon Transcribe (Vietnamese speech) and Amazon Rekognition (English labels & OCR text):\n'
            '   - Example "thầy dặn thi" -> ["dặn thi", "ôn thi", "cuối kỳ", "kiểm tra", "nội dung thi", "exam", "test", "final exam"]\n'
            '   - Example "ảnh chụp bảng môn mạng" -> ["mạng máy tính", "computer network", "packet", "IP", "TCP", "OSI", "router", "Whiteboard", "Classroom"]\n'
            '   - Example "hóa đơn cafe" -> ["hóa đơn", "tiền", "thanh toán", "cà phê", "receipt", "bill", "invoice", "coffee"]\n'
            "3. Map subject and category accurately:\n"
            '   - Non-CS courses -> subject: "off_major"\n'
            '   - General lecture whiteboard -> category: "study", subject: "lecture"\n'
            "   - If the query is not related to study/courses -> subject: null\n\n"
            "FEW-SHOT EXAMPLES:\n"
            'User: "tìm đoạn ghi âm thầy dặn ôn thi cuối kỳ môn mạng"\n'
            "Output:\n"
            "{\n"
            '  "keywords": ["dặn thi", "ôn thi", "cuối kỳ", "mạng máy tính", "computer network", "exam", "final"],\n'
            '  "media_type": "audio",\n'
            '  "category": "study",\n'
            '  "subject": "networks",\n'
            '  "rationale": "Truy vấn tìm đoạn ghi âm dặn thi học phần Mạng máy tính."\n'
            "}\n\n"
            'User: "ảnh chụp slide bài tập SQL database"\n'
            "Output:\n"
            "{\n"
            '  "keywords": ["SQL", "database", "cơ sở dữ liệu", "bài tập", "query", "table", "SELECT", "Slide", "Document"],\n'
            '  "media_type": "image",\n'
            '  "category": "study",\n'
            '  "subject": "database",\n'
            '  "rationale": "Truy vấn tìm hình ảnh slide bài tập môn Cơ sở dữ liệu."\n'
            "}"
        )
        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user_query}]}],
                inferenceConfig={"maxTokens": 350, "temperature": 0},
            )
            text = response["output"]["message"]["content"][0]["text"]
            plan = _parse_bedrock_plan_json(text, user_query)
            if cache_key and plan and plan.planner_source == "bedrock":
                if len(_PLAN_CACHE) >= _PLAN_CACHE_MAX_SIZE:
                    oldest = sorted(_PLAN_CACHE.keys(), key=lambda k: _PLAN_CACHE[k][0])[:50]
                    for k in oldest:
                        _PLAN_CACHE.pop(k, None)
                _PLAN_CACHE[cache_key] = (now, plan.model_copy(deep=True))
            return plan
        except Exception as exc:
            if _is_daily_token_throttle(exc):
                _mark_bedrock_daily_quota()
                return _heuristic_search_plan(
                    user_query,
                    "Bedrock hết hạn mức token trong ngày — đang tìm theo từ khóa. Thử lại sau vài giờ hoặc ngày mai.",
                )
            if _is_rate_throttle(exc):
                _mark_bedrock_rate_limit()
                return _heuristic_search_plan(
                    user_query,
                    "Bedrock đang bị giới hạn tốc độ — tìm theo từ khóa trong khoảng 1 phút.",
                )
            logger.warning("Bedrock plan error: %s. Using heuristic fallback.", exc)
            return _heuristic_search_plan(user_query, "Bedrock unavailable — keyword fallback")

    def synthesize_answer(self, user_query: str, hits: list) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Synthesize a direct answer and evidence snippet from top search hits."""
        if not hits or not user_query.strip() or _bedrock_quota_blocked() or _bedrock_rate_blocked():
            return None, None, None

        context_blocks = []
        for hit in hits[:3]:
            rec = getattr(hit, "record", hit)
            text_content = (getattr(rec, "transcript", "") or getattr(rec, "ocr_text", "") or getattr(rec, "summary", "")).strip()
            if text_content:
                snippet = text_content[:500]
                context_blocks.append(f"[File: {rec.filename} | Type: {rec.media_type}]\nContent: {snippet}")

        if not context_blocks:
            return None, None, None

        context_str = "\n\n".join(context_blocks)
        system = (
            "You are the AI Academic Assistant for AgentSys.\n"
            "Based on the provided media contexts, answer the user's question directly in Vietnamese.\n"
            "Return JSON with keys: direct_answer (concise answer, 2-3 sentences), evidence_snippet (exact quote), source_file (filename).\n"
            "Output ONLY raw JSON."
        )
        prompt = f"Question: {user_query}\n\nRetrieved Media Contexts:\n{context_str}"
        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 300, "temperature": 0},
            )
            raw = response["output"]["message"]["content"][0]["text"]
            cleaned = raw.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "{" in cleaned and "}" in cleaned:
                start = cleaned.find("{")
                end = cleaned.rfind("}") + 1
                cleaned = cleaned[start:end]
            data = json.loads(cleaned)
            return data.get("direct_answer"), data.get("evidence_snippet"), data.get("source_file")
        except Exception as exc:
            logger.debug("Bedrock synthesize_answer failed: %s", exc)
            return None, None, None


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


_PING_CACHE: dict = {"at": 0.0, "payload": None}


def ping_aws(ttl_seconds: float = 0) -> dict:
    now = time.monotonic()
    cached = _PING_CACHE["payload"]
    if ttl_seconds > 0 and cached and (now - float(_PING_CACHE["at"])) < ttl_seconds:
        return cached

    status = {
        "sts": "UNKNOWN",
        "s3": "UNKNOWN",
        "dynamodb": "UNKNOWN",
        "rekognition": "UNKNOWN",
        "transcribe": "UNKNOWN",
        "bedrock": "UNKNOWN",
    }
    errors: dict[str, str] = {}

    def mark(name: str, call) -> None:
        try:
            call()
            status[name] = "ONLINE"
        except ClientError as exc:
            err = exc.response.get("Error", {})
            code = err.get("Code", "")
            msg = err.get("Message", str(exc))
            # AccessDenied / AccessDeniedException → credentials valid but
            # IAM policy missing this specific action.  Service reachable.
            if "AccessDenied" in code or "Unauthorized" in code:
                status[name] = "UNKNOWN"
            else:
                status[name] = "OFFLINE"
            errors[name] = f"{code}: {msg}"
        except Exception as exc:
            status[name] = "OFFLINE"
            errors[name] = str(exc)

    mark("sts", lambda: _client("sts").get_caller_identity())
    mark("s3", lambda: _client("s3").head_bucket(Bucket=settings.MEDIA_BUCKET))
    mark("dynamodb", lambda: _client("dynamodb").describe_table(TableName=settings.METADATA_TABLE))
    mark("rekognition", lambda: _client("rekognition").list_collections(MaxResults=1))
    mark("transcribe", lambda: _client("transcribe").list_transcription_jobs(MaxResults=1))
    region = settings.BEDROCK_REGION or settings.AWS_REGION
    mark("bedrock", lambda: _client("bedrock", region=region).get_foundation_model(
        modelIdentifier=settings.BEDROCK_MODEL_ID,
    ))
    payload = {"status": status, "errors": errors}
    _PING_CACHE["at"] = now
    _PING_CACHE["payload"] = payload
    return payload
