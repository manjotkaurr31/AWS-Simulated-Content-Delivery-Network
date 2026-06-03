from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = FastAPI(
    title="My Mini CDN",
    description="Origin server backed by S3",
    version="1.0.0"
)

BUCKET_NAME = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")

ORIGIN_QUEUE_URL = os.getenv("ORIGIN_QUEUE_URL")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)

sqs = boto3.client(
    "sqs",
    region_name=AWS_REGION
)


def publish_event(
    event_type: str,
    filename: str
):
    sqs.send_message(
        QueueUrl=ORIGIN_QUEUE_URL,
        MessageBody=json.dumps(
            {
                "event_type": event_type,
                "filename": filename
            }
        )
    )


@app.get("/")
def root():
    return {
        "service": "origin",
        "status": "healthy"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/files")
def list_files():
    try:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME
        )

        files = [
            obj["Key"]
            for obj in response.get("Contents", [])
        ]

        return {
            "files": files
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/files/{filename}")
def get_file(filename: str):
    try:
        obj = s3.get_object(
            Bucket=BUCKET_NAME,
            Key=filename
        )

        return StreamingResponse(
            obj["Body"],
            media_type=obj.get(
                "ContentType",
                "application/octet-stream"
            ),
            headers={
                "Content-Disposition":
                f'inline; filename="{filename}"'
            }
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code in ["NoSuchKey", "404"]:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/files/upload")
def upload_file(
    file: UploadFile = File(...)
):
    try:

        existing_file = False

        try:
            s3.head_object(
                Bucket=BUCKET_NAME,
                Key=file.filename
            )
            existing_file = True

        except ClientError:
            pass

        s3.upload_fileobj(
            file.file,
            BUCKET_NAME,
            file.filename
        )

        if existing_file:
            publish_event(
                event_type="FILE_UPDATED",
                filename=file.filename
            )

        return {
            "message": "uploaded",
            "filename": file.filename,
            "existing_file": existing_file
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.delete("/files/{filename}")
def delete_file(filename: str):
    try:

        s3.delete_object(
            Bucket=BUCKET_NAME,
            Key=filename
        )

        publish_event(
            event_type="FILE_DELETED",
            filename=filename
        )

        return {
            "message": "deleted",
            "filename": filename
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
