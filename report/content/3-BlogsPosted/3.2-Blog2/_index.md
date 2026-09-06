---
title: "Blog 2"
date: 2024-01-01
weight: 2
chapter: false
pre: " <b> 3.2. </b> "
---

# Blog 2: Vietnamese Speech Transcription with Amazon Transcribe: Avoiding Timeouts and S3 Event Loops

In **AgentSys**, one of the most useful features is allowing students to retrieve recorded lectures by spoken queries (e.g. searching *"which exercises did the professor assign for the final exam"*).

We selected **Amazon Transcribe** for its native Vietnamese (`vi-VN`) speech-to-text accuracy. However, integrating it into a Serverless architecture revealed two classic operational traps.

---

## 1. Trap #1: Synchronous Waiting Causes Lambda Timeouts

Initially, our Lambda handler executed sequentially:
1. Receive uploaded audio.
2. Call `start_transcription_job()`.
3. Loop `time.sleep(5)` waiting for job status `COMPLETED`.
4. Persist transcript to DynamoDB.

**The Failure:**  
Short 15-second audio clips worked fine. But with real-world 3–5 minute lecture recordings, Transcribe took 40–60 seconds. The Lambda instance timed out, breached the 29-second API Gateway limit, and wasted execution billing.

**The Fix:**  
Transitioning to an **Asynchronous State Machine**:
* On upload, Lambda initializes the Transcribe Job, immediately writes an item to DynamoDB with `status: "INDEXING"`, and returns a response in `< 1s`.
* When Transcribe finishes, it drops the JSON artifact into S3, and the system finalizes the record state to `READY`.

---

## 2. Trap #2: The Infinite Recursive S3 Event Loop

A classic cloud mistake:
* S3 event notification configured for all bucket objects: *"Trigger Lambda whenever any object is created"*.
* User uploads `audio.mp3` $\rightarrow$ S3 triggers Lambda $\rightarrow$ Lambda triggers Transcribe.
* Transcribe outputs `transcript.json` into the same bucket $\rightarrow$ **S3 sees a new object and triggers Lambda again $\rightarrow$ Lambda starts another Transcribe job...**

**The Fix:**  
Enforce strict S3 prefix segregation:
* S3 Event Notifications strictly filter on **`Prefix: uploads/`**.
* Transcribe outputs are routed to **`Prefix: transcripts/`**.

---

## 3. Optimizing Vietnamese Speech Transcription

* **Recommended Formats:** Use compressed formats like `.m4a` (AAC) or `.mp3` rather than heavy `.wav` files to reduce upload latency.
* **Language Setting:** Set `LanguageCode: "vi-VN"`.
* **Cost:** At `$0.024 / minute`, 60 minutes free per month in Free Tier comfortably accommodates testing.

---

> 📝 **Published on [AWS Study Group — Facebook Community](https://www.facebook.com/groups/awsstudygroupfcj)** as part of the FCAJ internship blog requirement.
