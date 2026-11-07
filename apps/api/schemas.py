from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class UploadUrlRequest(BaseModel):
    filename: str = Field(..., examples=["lecture-board.jpg"])
    content_type: str = Field(..., examples=["image/jpeg"])
    size_bytes: Optional[int] = Field(default=None, description="Kích thước tệp tính bằng bytes")


class UploadUrlResponse(BaseModel):
    file_id: str
    presigned_url: str
    object_key: str
    method: str = "PUT"
    upload_url: Optional[str] = None


class ProcessRequest(BaseModel):
    file_id: str
    object_key: Optional[str] = None
    filename: Optional[str] = None
    content_type: str = ""


class StatusResponse(BaseModel):
    file_id: str
    status: str
    error: Optional[str] = None


class AgentQueryRequest(BaseModel):
    user_query: str = Field(default="", examples=["Tìm đoạn thầy dặn thi cuối kỳ"])
    query: Optional[str] = None
    file_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def unify_query(cls, data: Any) -> Any:
        if isinstance(data, dict):
            q = data.get("user_query") or data.get("query") or ""
            data["user_query"] = q
        return data


class MediaItemOut(BaseModel):
    id: str
    filename: str
    type: str
    url: str
    thumbnailUrl: Optional[str] = None
    size: str
    date: str
    category: str
    categoryLabel: str
    labels: List[str]
    ocrText: str = ""
    transcript: str = ""
    summary: str = ""
    status: str
    tags: List[str]
    source: str
    score: Optional[float] = None
    matchedOn: List[str] = Field(default_factory=list)
    matchedFields: List[str] = Field(default_factory=list)
    pipeline: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    analysisSource: str = ""
    subject: str = "none"
    subjectLabel: str = ""
    transcript_s3_uri: Optional[str] = None
    has_extended_transcript: bool = False
    transcriptS3Uri: Optional[str] = None
    hasExtendedTranscript: bool = False
    is_demo_protected: bool = False
    isDemoProtected: bool = False


class AgentQueryResponse(BaseModel):
    user_query: str
    execution_status: str
    plan: Dict[str, Any]
    results: List[MediaItemOut]
