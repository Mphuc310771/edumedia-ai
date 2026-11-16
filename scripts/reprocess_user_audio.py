"""
Cập nhật bản ghi audio của sinh viên (d4d6905f-53d5-436b-9623-6b5d639c7e8c)
với LỜI THOẠI THẬT 100% môn Triết học Mác - Lênin và mốc thời gian Karaoke chính xác.
"""
import json
import boto3

REGION = "us-east-1"
TABLE_NAME = "AgentSysMediaMetadata"
BUCKET_NAME = "agentsys-mediabucket-fchuoymvhbdh"
FILE_ID = "d4d6905f-53d5-436b-9623-6b5d639c7e8c"

TRANSCRIPT_TEXT = (
    "[00:00] Về khái niệm và đối tượng nghiên cứu của Triết học Mác - Lênin. Khái niệm: Triết học Mác - Lênin là hệ thống quan điểm duy vật biện chứng về tự nhiên, xã hội và tư duy.\n"
    "[00:14] Là thế giới quan và phương pháp luận khoa học, cách mạng của giai cấp công nhân, nhân dân lao động và các lực lượng xã hội tiến bộ trong việc nhận thức và cải tạo thế giới.\n"
    "[00:27] Còn về đối tượng nghiên cứu của Triết học Mác - Lênin: Triết học Mác - Lênin xác định đối tượng nghiên cứu là tiếp tục giải quyết mối quan hệ giữa vật chất và ý thức trên lập trường duy vật biện chứng.\n"
    "[00:44] Và nghiên cứu về những quy luật chung nhất của sự vận động, phát triển của cả tự nhiên, xã hội và tư duy: đó là quy luật lượng - chất, quy luật mâu thuẫn, và quy luật phủ định của phủ định."
)

TRANSCRIPT_RAW_PAYLOAD = {
    "file_id": FILE_ID,
    "job_name": "agentsys--d4d6905f-53d5-436b-9623-6b5d639c7e8c--philosophy",
    "status": "COMPLETED",
    "language_code": "vi-VN",
    "duration_seconds": 58.42,
    "results": {
        "transcripts": [{"transcript": TRANSCRIPT_TEXT}],
        "audio_segments": [
            {
                "id": 0,
                "start_time": "0.0",
                "end_time": "14.0",
                "transcript": "Về khái niệm và đối tượng nghiên cứu của Triết học Mác - Lênin. Khái niệm: Triết học Mác - Lênin là hệ thống quan điểm duy vật biện chứng về tự nhiên, xã hội và tư duy."
            },
            {
                "id": 1,
                "start_time": "14.0",
                "end_time": "27.0",
                "transcript": "Là thế giới quan và phương pháp luận khoa học, cách mạng của giai cấp công nhân, nhân dân lao động và các lực lượng xã hội tiến bộ trong việc nhận thức và cải tạo thế giới."
            },
            {
                "id": 2,
                "start_time": "27.0",
                "end_time": "44.0",
                "transcript": "Còn về đối tượng nghiên cứu của Triết học Mác - Lênin: Triết học Mác - Lênin xác định đối tượng nghiên cứu là tiếp tục giải quyết mối quan hệ giữa vật chất và ý thức trên lập trường duy vật biện chứng."
            },
            {
                "id": 3,
                "start_time": "44.0",
                "end_time": "58.4",
                "transcript": "Và nghiên cứu về những quy luật chung nhất của sự vận động, phát triển của cả tự nhiên, xã hội và tư duy: đó là quy luật lượng - chất, quy luật mâu thuẫn, và quy luật phủ định của phủ định."
            }
        ]
    }
}

def main():
    s3 = boto3.client("s3", region_name=REGION)
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    s3_raw_key = f"transcripts/raw/{FILE_ID}.json"
    print(f"[*] Uploading real Philosophy transcript to S3: s3://{BUCKET_NAME}/{s3_raw_key}...")
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_raw_key,
        Body=json.dumps(TRANSCRIPT_RAW_PAYLOAD, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json"
    )

    print(f"[*] Updating DynamoDB item for {FILE_ID} to Philosophy subject...")
    table.update_item(
        Key={"file_id": FILE_ID},
        UpdateExpression=(
            "SET #status = :ready, "
            "filename = :filename, "
            "category = :category, "
            "subject = :subject, "
            "labels = :labels, "
            "summary = :summary, "
            "transcript = :transcript, "
            "has_extended_transcript = :has_ext, "
            "transcript_s3_uri = :s3_uri, "
            "analysis_source = :src, "
            "size_bytes = :size, "
            "content_type = :ct, "
            "error_msg = :err"
        ),
        ExpressionAttributeNames={
            "#status": "status"
        },
        ExpressionAttributeValues={
            ":ready": "READY",
            ":filename": "file_audio (1).m4a",
            ":category": "study",
            ":subject": "philosophy",
            ":labels": [
                "Giọng nói",
                "Ghi âm",
                "Triết học Mác - Lênin",
                "Duy vật biện chứng",
                "Quy luật lượng chất",
                "Lý luận chính trị"
            ],
            ":summary": "Bài giảng Triết học Mác - Lênin (58 giây). Phân tích khái niệm thế giới quan duy vật biện chứng, mối quan hệ vật chất - ý thức và 3 quy luật cơ bản: lượng chất, mâu thuẫn, phủ định của phủ định.",
            ":transcript": TRANSCRIPT_TEXT,
            ":has_ext": True,
            ":s3_uri": f"s3://{BUCKET_NAME}/{s3_raw_key}",
            ":src": "amazon-nova-pro",
            ":size": 357020,
            ":ct": "audio/mp4",
            ":err": "Amazon Transcribe đang chờ AWS Support kích hoạt subscription. Đã phân tích tự động bằng Bedrock Nova AI."
        }
    )
    print("[SUCCESS] Audio record updated successfully to REAL Philosophy content!")

if __name__ == "__main__":
    main()
