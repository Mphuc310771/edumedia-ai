"""
Re-transcribe existing audio files in DynamoDB using speech transcriber.
"""
from apps.aws.providers import get_runtime
from apps.workers.ingestion import _build_summary

def run():
    runtime = get_runtime()
    items = runtime.catalog.list_all()
    audio_items = [i for i in items if i.media_type == "audio"]
    print(f"[*] Found {len(audio_items)} audio records in DynamoDB.")

    for item in audio_items:
        safe_fn = item.filename.encode("ascii", "replace").decode("ascii")
        print(f"[*] Transcribing audio: {safe_fn} (S3 key: {item.s3_key})...")
        ext = item.filename.rsplit(".", 1)[-1].lower() if "." in item.filename else "mp4"
        speech_text = runtime.speech.transcribe(item.s3_key, ext)
        if speech_text and not speech_text.startswith("Bản ghi"):
            item.transcript = speech_text
            item.summary = _build_summary(item)
            runtime.catalog.put(item)
            safe_text = speech_text[:80].encode("ascii", "replace").decode("ascii")
            print(f"  [OK] Successfully transcribed: \"{safe_text}...\"")
        else:
            safe_out = speech_text[:50].encode("ascii", "replace").decode("ascii")
            print(f"  [INFO] Speech output: {safe_out}")

    print("==================================================")
    print("[SUCCESS] AUDIO RE-TRANSCRIPTION COMPLETE!")
    print("==================================================")

if __name__ == "__main__":
    run()
