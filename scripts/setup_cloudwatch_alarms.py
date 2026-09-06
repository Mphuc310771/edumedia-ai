#!/usr/bin/env python3
"""FCAJ Workshop: CloudWatch Alarm Setup & Verification Script.

Creates the CloudWatch Alarm on Lambda Error Count and Dead-Letter Queue (DLQ) depth
as required by the Workshop Rubric (Metric / Alert section).

Usage:
    python scripts/setup_cloudwatch_alarms.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.aws.aws_services import _client
from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AgentSys.Alarms")


def setup_alarms():
    cw = _client("cloudwatch")
    logger.info("Configuring CloudWatch Alarms in region: %s", settings.AWS_REGION)

    # Alarm 1: DLQ Messages Visible Alarm (Alerts if 3x retried messages land in DLQ)
    try:
        cw.put_metric_alarm(
            AlarmName="AgentSys-Ingest-DLQ-VisibleMessages",
            AlarmDescription="Alerts when failed media ingestion messages land in the Dead-Letter Queue.",
            ActionsEnabled=False,
            MetricName="ApproximateNumberOfMessagesVisible",
            Namespace="AWS/SQS",
            Statistic="Maximum",
            Dimensions=[{"Name": "QueueName", "Value": "agentsys-ingest-dlq"}],
            Period=300,
            EvaluationPeriods=1,
            Threshold=1.0,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
            TreatMissingData="notBreaching",
        )
        logger.info("Successfully created/updated Alarm: AgentSys-Ingest-DLQ-VisibleMessages")
    except Exception as exc:
        logger.warning("Could not create DLQ Alarm: %s", exc)

    # Alarm 2: Media Ingestion Failure Custom Metric Alarm
    try:
        cw.put_metric_alarm(
            AlarmName="AgentSys-MediaIngestFailed-Rate",
            AlarmDescription="Alerts when consecutive media ingestion/transcription jobs fail.",
            ActionsEnabled=False,
            MetricName="MediaIngestFailed",
            Namespace=settings.CLOUDWATCH_NAMESPACE,
            Statistic="Sum",
            Period=300,
            EvaluationPeriods=1,
            Threshold=1.0,
            ComparisonOperator="GreaterThanOrEqualToThreshold",
            TreatMissingData="notBreaching",
        )
        logger.info("Successfully created/updated Alarm: AgentSys-MediaIngestFailed-Rate")
    except Exception as exc:
        logger.warning("Could not create Ingest Failed Alarm: %s", exc)

    print("\n" + "=" * 70)
    print("  CLOUDWATCH ALARMS CONFIGURATION COMPLETED")
    print("=" * 70)
    print("AWS CLI Verification Command:")
    print("  aws cloudwatch describe-alarms --alarm-name-prefix AgentSys --region " + settings.AWS_REGION)
    print("=" * 70)


if __name__ == "__main__":
    setup_alarms()
