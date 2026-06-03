import json
import os
import time

from dotenv import load_dotenv
import boto3

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
ORIGIN_QUEUE_URL = os.getenv("ORIGIN_QUEUE_URL")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")

print("Invalidation service starting...", flush=True)
print(f"AWS_REGION={AWS_REGION}", flush=True)
print(f"QUEUE={ORIGIN_QUEUE_URL}", flush=True)
print(f"TOPIC={SNS_TOPIC_ARN}", flush=True)

sqs = boto3.client(
    "sqs",
    region_name=AWS_REGION
)

sns = boto3.client(
    "sns",
    region_name=AWS_REGION
)


def process_message(message):
    body = json.loads(message["Body"])

    print(f"Received: {body}", flush=True)

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(body)
    )

    print("Published to SNS", flush=True)

    sqs.delete_message(
        QueueUrl=ORIGIN_QUEUE_URL,
        ReceiptHandle=message["ReceiptHandle"]
    )

    print("Deleted from queue", flush=True)


def main():
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=ORIGIN_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            messages = response.get("Messages", [])

            if not messages:
                print("Polling...", flush=True)
                continue

            for message in messages:
                process_message(message)

        except Exception as e:
            print(f"ERROR: {e}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
