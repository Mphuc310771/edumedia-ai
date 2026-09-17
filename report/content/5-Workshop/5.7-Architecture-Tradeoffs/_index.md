---
title: "Architecture Trade-offs & Enterprise Roadmap"
date: 2024-01-01
weight: 7
chapter: false
pre: " <b> 5.7. </b> "
---

# 5.7. Discussion: Architecture Trade-offs & Enterprise Roadmap

During the initial Proof of Concept (PoC) phase for the First Cloud AI Journey (FCAJ), the core engineering objective for AgentSys was to build a production-grade multimodal AI media catalog while adhering strictly to a **Zero-Idle-Cost, Lean Serverless architecture**.

To strike the right balance between rapid experimental learning and cost-effectiveness, deliberate architectural trade-offs were made. Below is a rigorous technical evaluation of the 4 key limitations of the current architecture along with target enterprise-grade AWS solutions for production scale.

---

### 1. In-Memory Vector Search on Lambda RAM
* **Current PoC Status:**
  DynamoDB is a document/key-value NoSQL database without native Approximate Nearest Neighbor (ANN) vector indexing. AgentSys implements a Two-Stage Search strategy: Amazon Bedrock acts as Query Planner extracting metadata categories for sub-15ms DynamoDB GSI queries (`category-index`), followed by in-memory Cosine Similarity scoring over a capped candidate pool (100 newest items) within Lambda RAM.
* **Limitations:**
  While providing zero idle cost, capping the candidate pool at 100 items causes recall degradation when catalogs exceed tens of thousands of items. Conversely, unbounded table scans incur linear $O(N)$ cost and latency penalties.
* **AWS Enterprise Target:**
  - Transition to **Amazon OpenSearch Serverless (Vector Engine)** or **Amazon Aurora Serverless (PostgreSQL + `pgvector`)**.
  - Vectors are indexed using HNSW or IVF algorithms directly in storage, achieving sub-20ms k-NN retrieval across millions of records without moving raw embeddings into Lambda RAM.

---

### 2. Vector Dimensionality & Amazon Titan Embeddings V2 Upgrade
* **Current PoC Status:**
  Earlier implementations subsampled 1536-d vectors to 256-d via uniform index striding to reduce DynamoDB item storage below 400KB limits.
* **Limitations:**
  Neural embedding latent dimensions are non-linear; uniform subsampling degrades topological semantic manifold structure.
* **AWS Enterprise Target:**
  - Upgraded to native **Amazon Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`)**, which natively supports Matryoshka Representation Learning with direct `dimensions: 256` and `normalize: true` parameterization.
  - Future roadmap includes **Amazon Titan Multimodal Embeddings** to unify image, audio, and text vectors into a single joint vector space.

---

### 3. DynamoDB Schema & Chunk Scan Overhead
* **Current PoC Status:**
  `AgentSysMediaMetadata` uses a simple primary key (`file_id`). Lecture transcript chunks are stored using composite IDs (`file_id#CHUNK#0001`), requiring DynamoDB FilterExpressions during chunk aggregation.
* **Limitations:**
  FilterExpressions evaluate after disk reads, consuming Read Capacity Units (RCUs) across irrelevant records.
* **AWS Enterprise Target:**
  - Normalize to a true **DynamoDB Single-Table Design**:
    - **Partition Key (`PK`):** `FILE#<file_id>`
    - **Sort Key (`SK`):** `METADATA` or `CHUNK#<index>`
  - Chunk queries become single partition reads: `Query(PK='FILE#123', SK begins_with 'CHUNK#')` with exact $O(k)$ complexity.

---

### 4. Distributed Map-Reduce for Long Lectures
* **Current PoC Status:**
  Upon Transcribe completion, an EventBridge rule triggers a Lambda worker that sequentially refines chunks with Bedrock and performs reduction, paired with DynamoDB Streams for race condition defense.
* **Limitations:**
  For 1-2 hour lectures (40-80 chunks), sequential LLM inference risks hitting Lambda's execution timeout limit.
* **AWS Enterprise Target:**
  - Replace sequential Lambda loops with **AWS Step Functions Distributed Map**:
    1. **Split State:** Chunk transcript and store in S3/DynamoDB.
    2. **Distributed Map:** Fan-out up to 50 concurrent Lambda workers running Bedrock chunk refinement in parallel.
    3. **Reduce State:** Fan-in and aggregate final structured summaries.
  - Reduces total processing time from minutes to under 10 seconds while eliminating timeout risks.

---

### 📊 Comparison Summary: PoC vs. Enterprise Production Architecture

| Technical Criteria | AgentSys PoC (Current) | Enterprise Production Target |
| :--- | :--- | :--- |
| **Vector Search Engine** | Candidate Pool (100) + In-Memory Cosine | Amazon OpenSearch Serverless / pgvector (HNSW) |
| **Embedding Space** | Titan v2 (256-d native) + v1 Fallback | Titan Multimodal Embeddings V2 (256-d / 1024-d) |
| **Data Model** | Single PK (`file_id`) + FilterExpression | Composite Key (`PK: FILE#id`, `SK: CHUNK#idx`) |
| **Map-Reduce Orchestration**| EventBridge Worker + Streams Demo | AWS Step Functions (Distributed Map State) |
| **Audio Processing Latency**| Sequential $O(N)$ per chunk | Concurrent $O(1)$ distributed fan-out |
| **Idle Infrastructure Cost**| **$0.00 / month** (Zero-Idle Serverless) | ~$20–$50 / month (OpenSearch Serverless OCU baseline) |
| **Core Objective** | Cost optimization, rapid lab demo, PoC | Scalability to millions of records, Enterprise SLA |
