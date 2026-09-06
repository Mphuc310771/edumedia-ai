---
title: "Blog 1"
date: 2024-01-01
weight: 1
chapter: false
pre: " <b> 3.1. </b> "
---

# Blog 1: Practical Lessons from Using Amazon Rekognition for Classroom OCR and Image Labeling

When building **AgentSys**—a multi-modal study asset catalog for students—the very first challenge was: **How do we find classroom whiteboard photos and lecture slides when a student searches with natural language?**

Initially, I considered deploying open-source OCR models (like PaddleOCR or EasyOCR) on an EC2 instance. However, student workloads are bursty; paying ~$40–$50/month for an idle GPU server made little financial sense. Transitioning to **Amazon Rekognition** under a Serverless model solved this seamlessly.

Here are the practical engineering takeaways from integrating Rekognition.

---

## 1. Running DetectLabels and DetectText in Tandem

To properly index multimedia assets, relying exclusively on either OCR or object detection is insufficient:
* Using only `DetectText`: Vacation photos or campus snapshots lacking written text would have zero semantic tags.
* Using only `DetectLabels`: Photos of complex blackboard math equations would only receive generic tags like `Blackboard` or `Text`, missing all equation content.

In the ingestion worker, we invoke both APIs concurrently:

```python
# Extract semantic categories
labels_res = rekognition.detect_labels(
    Image={"S3Object": {"Bucket": bucket, "Name": key}},
    MaxLabels=10,
    MinConfidence=70.0
)

# Extract lecture board content for keyword search
text_res = rekognition.detect_text(
    Image={"S3Object": {"Bucket": bucket, "Name": key}}
)
```

---

## 2. Handling Real-World Noise in Handwritten OCR

During testing with real classroom chalkboard photos, `DetectText` returned fragmented text artifacts (faint chalk dust streaks, isolated punctuation marks). Ingesting these raw fragments degraded vector embedding quality.

We implemented a lightweight heuristic filter in `apps/domain.py`:

```python
def is_noise_ocr_line(text: str) -> bool:
    """Filter out noisy non-semantic OCR fragments"""
    clean = text.strip()
    if len(clean) <= 1:
        return True
    if clean.isdigit() and len(clean) < 3:
        return True
    return False
```

This simple pre-filter cleansed metadata significantly, ensuring only meaningful formulas, headings, and bullet points entered the database.

---

## 3. Real-World FinOps & Latency

* Each image running both `DetectLabels` ($0.001) and `DetectText` ($0.001) costs a total of **$0.002 (≈ 50 VNĐ)**.
* With 1,000 free images per month in the AWS Free Tier, our development and test suites operated at $0 cost.
* Average end-to-end execution time was **400ms – 600ms** per 4K image.

---

> 📝 **Published on [AWS Study Group — Facebook Community](https://www.facebook.com/groups/awsstudygroupfcj)** as part of the FCAJ internship blog requirement.
