from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UploadUrlRequest(BaseModel):
    filename: str = Field(..., examples=["lecture-board.jpg"])
    content_type: str = Field(..., examples=["image/jpeg"])


class UploadUrlResponse(BaseModel):
    file_id: str
    presigned_url: str
    object_key: str
    method: str = "PUT"


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
    user_query: str = Field(..., examples=["Tìm đoạn thầy dặn thi cuối kỳ"])
    file_id: Optional[str] = None


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


class AgentQueryResponse(BaseModel):
    user_query: str
    execution_status: str
    plan: Dict[str, Any]
    results: List[MediaItemOut]
