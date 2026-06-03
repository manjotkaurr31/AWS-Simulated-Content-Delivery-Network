import hashlib
import json
import os
import time

import boto3

AWS_REGION = os.getenv("AWS_REGION")
QUEUE_URL = os.getenv("QUEUE_URL")
CACHE_ROOT = os.getenv("CACHE_ROOT")

print("Edge worker started", flush=True)
print(f"AWS_REGION={AWS_REGION}", flush=True)
print(f"QUEUE_URL={QUEUE_URL}", flush=True)
print(f"CACHE_ROOT={CACHE_ROOT}", flush=True)

sqs = boto3.client(
    "sqs",
    region_name=AWS_REGION
)


def purge_file(filename: str):

    cache_key = f"/files/{filename}"

    md5_hash = hashlib.md5(
        cache_key.encode()
    ).hexdigest()

    level1 = md5_hash[-1]
    level2 = md5_hash[-3:-1]

    cache_file = (
        f"{CACHE_ROOT}/"
        f"{level1}/"
        f"{level2}/"
        f"{md5_hash}"
    )

    print(f"\nPurging: {filename}", flush=True)
    print(f"Path: {cache_file}", flush=True)

    if os.path.exists(cache_file):
        os.remove(cache_file)
        print("Purged successfully", flush=True)
    else:
        print("Cache file not found", flush=True)


def main():

    while True:

        try:

            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            messages = response.get(
                "Messages",
                []
            )

            if not messages:
                print("Polling...", flush=True)
                continue

            for message in messages:

                body = json.loads(
                    message["Body"]
                )

                if "Message" in body:
                    payload = json.loads(
                        body["Message"]
                    )
                else:
                    payload = body

                filename = payload["filename"]

                purge_file(filename)

                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"]
                )

                print("Message deleted", flush=True)

            time.sleep(1)

        except Exception as e:

            print(
                f"ERROR: {str(e)}",
                flush=True
            )

            time.sleep(5)


if __name__ == "__main__":
    main()
