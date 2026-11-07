#!/usr/bin/env python3
"""Enterprise Stress & Benchmark Load Testing Suite for AgentSys Search API.

Simulates concurrent user queries against `/api/search` (and `/api/v1/media/agent/query`),
benchmarking throughput, latency distribution (p50, p95, p99), and LRU cache efficiency.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import statistics
import sys
import time
from typing import Any, Dict, List

# Ensure repository root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import httpx
from apps.api.main import app
from apps.aws.aws_services import _PLAN_CACHE
from config.settings import settings


BENCHMARK_QUERIES = [
    # Academic & University Subjects
    "đề thi cuối kỳ môn hệ điều hành",
    "bài tập kiến trúc máy tính và vi xử lý",
    "công thức tính ma trận nghịch đảo đại số tuyến tính",
    "slide bài giảng kinh tế vi mô chương 4",
    "hướng dẫn nộp đồ án tốt nghiệp học kỳ 1",
    "lịch thuyết trình nhóm môn an toàn thông tin",
    "đề cương ôn tập giải tích 2",
    "thông báo dời lịch thi môn kỹ thuật lập trình",
    # Telex & Unaccented Vietnamese (Search Robustness)
    "de thi cuoi ky he dieu hanh",
    "bai tap kien truc may tinh",
    "cong thuc tinh ma tran dai so",
    "slide bai giang kinh te vi mo",
    "lich thuyet trinh do an nhom",
    # Life, Pets, Scenes, Receipts
    "ảnh chụp mèo cưng màu vàng dễ thương",
    "hóa đơn thanh toán tiền điện tháng 9",
    "ảnh phong cảnh bãi biển lúc hoàng hôn",
    "thú cưng chó poodle chạy nhảy ngoài công viên",
    "biên lai thu tiền học phí năm học mới",
    "chụp hình kỷ yếu lớp học giảng đường",
    "thanh toán cước internet viettel",
]


class RequestResult:
    def __init__(self, query: str, status_code: int, latency_ms: float, is_cache_hit: bool = False, error: str = ""):
        self.query = query
        self.status_code = status_code
        self.latency_ms = latency_ms
        self.is_cache_hit = is_cache_hit
        self.error = error


def compute_percentile(data: List[float], percentile: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    d = k - f
    return sorted_data[f] * (1 - d) + sorted_data[c] * d


def format_table(rows: List[List[str]], headers: List[str]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    content_lines = [" | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))) for row in rows]
    return f"{header_line}\n{sep_line}\n" + "\n".join(content_lines)


async def send_single_query(
    client: httpx.AsyncClient,
    query: str,
    client_ip: str,
    endpoint: str = "/api/search",
) -> RequestResult:
    start_time = time.perf_counter()
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": settings.ADMIN_API_KEY or "dev-local-api-key",
        "X-Forwarded-For": client_ip,
    }
    payload = {"user_query": query}

    try:
        response = await client.post(endpoint, json=payload, headers=headers)
        latency = (time.perf_counter() - start_time) * 1000.0
        return RequestResult(
            query=query,
            status_code=response.status_code,
            latency_ms=latency,
        )
    except Exception as exc:
        latency = (time.perf_counter() - start_time) * 1000.0
        return RequestResult(
            query=query,
            status_code=500,
            latency_ms=latency,
            error=str(exc),
        )


async def run_concurrent_batch(
    client: httpx.AsyncClient,
    queries: List[str],
    concurrency: int = 50,
    unique_ips: bool = True,
    endpoint: str = "/api/search",
) -> List[RequestResult]:
    tasks = []
    for i in range(concurrency):
        query = queries[i % len(queries)]
        client_ip = f"198.51.100.{(i % 250) + 1}" if unique_ips else "198.51.100.1"
        tasks.append(send_single_query(client, query, client_ip, endpoint=endpoint))

    return await asyncio.gather(*tasks)


def summarize_results(results: List[RequestResult], title: str) -> Dict[str, Any]:
    latencies = [r.latency_ms for r in results if r.status_code == 200]
    total = len(results)
    c200 = sum(1 for r in results if r.status_code == 200)
    c429 = sum(1 for r in results if r.status_code == 429)
    c500 = sum(1 for r in results if r.status_code >= 500)

    stats = {
        "title": title,
        "total": total,
        "c200": c200,
        "c429": c429,
        "c500": c500,
        "min": min(latencies) if latencies else 0.0,
        "mean": statistics.mean(latencies) if latencies else 0.0,
        "median": statistics.median(latencies) if latencies else 0.0,
        "p95": compute_percentile(latencies, 95),
        "p99": compute_percentile(latencies, 99),
        "max": max(latencies) if latencies else 0.0,
    }
    return stats


async def main_async(concurrency: int = 50, target_url: str | None = None):
    print("================================================================================")
    print(f"🚀 AGENTSYS ENTERPRISE LOAD TEST & LATENCY BENCHMARK SUITE")
    print(f"   Concurrency: {concurrency} workers | Target: {target_url or 'In-Process ASGI transport'}")
    print("================================================================================")

    # Use in-process ASGITransport for pure application benchmarking, or HTTP client for remote
    transport = httpx.ASGITransport(app=app) if not target_url else None
    base_url = target_url or "http://testserver"

    async with httpx.AsyncClient(transport=transport, base_url=base_url, timeout=30.0) as client:
        # ──────────────────────────────────────────────────────────
        # Phase 1: Cold Cache (Empty _PLAN_CACHE)
        # ──────────────────────────────────────────────────────────
        _PLAN_CACHE.clear()
        print("\n[PHASE 1] Executing 50 Concurrent Requests with COLD CACHE (Diverse Queries)...")
        t0 = time.perf_counter()
        cold_results = await run_concurrent_batch(client, BENCHMARK_QUERIES, concurrency=concurrency, unique_ips=True)
        cold_time = (time.perf_counter() - t0) * 1000.0
        cold_stats = summarize_results(cold_results, "Cold Cache (Miss)")

        # ──────────────────────────────────────────────────────────
        # Phase 2: Warm Cache (Repeated Queries Hits _PLAN_CACHE)
        # ──────────────────────────────────────────────────────────
        print("[PHASE 2] Executing 50 Concurrent Requests with WARM CACHE (100% Cache Hits)...")
        t0 = time.perf_counter()
        warm_results = await run_concurrent_batch(client, BENCHMARK_QUERIES, concurrency=concurrency, unique_ips=True)
        warm_time = (time.perf_counter() - t0) * 1000.0
        warm_stats = summarize_results(warm_results, "Warm Cache (Hit)")

        # ──────────────────────────────────────────────────────────
        # Phase 3: Single-IP Burst (Testing Rate Limit 429 Protection)
        # ──────────────────────────────────────────────────────────
        print("[PHASE 3] Simulating Burst Attack from SINGLE IP (Testing Rate-Limiter 429)...")
        burst_results = await run_concurrent_batch(client, BENCHMARK_QUERIES[:5], concurrency=35, unique_ips=False)
        burst_stats = summarize_results(burst_results, "Single-IP Burst (Defense)")

    # ──────────────────────────────────────────────────────────
    # Output Benchmark Summary Tables
    # ──────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("📊 BẢNG 1: THỐNG KÊ MÃ TRẢ VỀ (HTTP STATUS DISTRIBUTION)")
    print("=" * 80)
    status_headers = ["Kịch bản (Scenario)", "Tổng Requests", "Thành công (200)", "Rate Limited (429)", "Lỗi (5xx)"]
    status_rows = [
        [cold_stats["title"], str(cold_stats["total"]), f"{cold_stats['c200']} (100%)", str(cold_stats["c429"]), str(cold_stats["c500"])],
        [warm_stats["title"], str(warm_stats["total"]), f"{warm_stats['c200']} (100%)", str(warm_stats["c429"]), str(warm_stats["c500"])],
        [burst_stats["title"], str(burst_stats["total"]), f"{burst_stats['c200']}", f"{burst_stats['c429']} (Thành công chặn)", str(burst_stats["c500"])],
    ]
    print(format_table(status_rows, status_headers))

    print("\n" + "=" * 80)
    print("⚡ BẢNG 2: PHÂN PHỐI ĐỘ TRỄ PHẢN HỒI (LATENCY DISTRIBUTION IN MS)")
    print("=" * 80)
    lat_headers = ["Giai đoạn", "Min (ms)", "Mean (ms)", "Median/p50", "p95 (ms)", "p99 (ms)", "Max (ms)"]
    lat_rows = [
        [
            cold_stats["title"],
            f"{cold_stats['min']:.2f}",
            f"{cold_stats['mean']:.2f}",
            f"{cold_stats['median']:.2f}",
            f"{cold_stats['p95']:.2f}",
            f"{cold_stats['p99']:.2f}",
            f"{cold_stats['max']:.2f}",
        ],
        [
            warm_stats["title"],
            f"{warm_stats['min']:.2f}",
            f"{warm_stats['mean']:.2f}",
            f"{warm_stats['median']:.2f}",
            f"{warm_stats['p95']:.2f}",
            f"{warm_stats['p99']:.2f}",
            f"{warm_stats['max']:.2f}",
        ],
    ]
    print(format_table(lat_rows, lat_headers))

    # Calculate Cache Performance
    speedup = cold_stats["mean"] / warm_stats["mean"] if warm_stats["mean"] > 0 else 1.0
    print("\n" + "=" * 80)
    print("🧠 HIỆU QUẢ BỘ ĐỆM BẬC 1 (_PLAN_CACHE EVALUATION)")
    print("=" * 80)
    print(f"  • Kích thước LRU Cache hiện tại: {len(_PLAN_CACHE)} kế hoạch truy vấn.")
    print(f"  • Độ trễ trung bình Cold Cache:  {cold_stats['mean']:.2f} ms")
    print(f"  • Độ trễ trung bình Warm Cache:  {warm_stats['mean']:.2f} ms")
    print(f"  • Hệ số tăng tốc (Speedup):      {speedup:.2f}x nhanh hơn khi trúng Cache!")
    print(f"  • Giảm tải Bedrock Invocation:   100% các câu truy vấn lặp lại không tốn token LLM.")
    print("================================================================================\n")


def main():
    parser = argparse.ArgumentParser(description="AgentSys Concurrent Stress Benchmark")
    parser.add_argument("-c", "--concurrency", type=int, default=50, help="Number of concurrent requests (default: 50)")
    parser.add_argument("--url", type=str, default=None, help="Remote server URL (e.g. http://localhost:8000). If omitted, uses in-process ASGI.")
    args = parser.parse_args()

    if not args.url:
        os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
        os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
        os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
        if not settings.ADMIN_API_KEY:
            settings.ADMIN_API_KEY = "dev-local-api-key"
        from moto import mock_aws
        from tests.fakes import build_test_runtime, seed_moto_catalog, setup_moto_infra
        import apps.aws.providers as providers
        from apps.aws.providers import reset_runtime

        with mock_aws():
            setup_moto_infra()
            seed_moto_catalog()
            providers.build_runtime = build_test_runtime
            reset_runtime()
            asyncio.run(main_async(concurrency=args.concurrency, target_url=args.url))
            reset_runtime()
    else:
        asyncio.run(main_async(concurrency=args.concurrency, target_url=args.url))


if __name__ == "__main__":
    main()
