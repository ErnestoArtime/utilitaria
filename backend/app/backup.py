import asyncio
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess
from urllib.parse import urlparse

import boto3


BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/backups"))


def database_parts() -> tuple[str, str, str, str, str]:
    parsed = urlparse(os.environ["DATABASE_URL"].replace("postgresql+psycopg", "postgresql"))
    return (
        parsed.hostname or "db",
        str(parsed.port or 5432),
        parsed.username or "utilitaria",
        parsed.password or "",
        parsed.path.lstrip("/"),
    )


def create_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    host, port, user, password, database = database_parts()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = BACKUP_DIR / f"utilitaria-{timestamp}.dump"
    environment = {**os.environ, "PGPASSWORD": password}
    subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--host",
            host,
            "--port",
            port,
            "--username",
            user,
            "--dbname",
            database,
            "--file",
            str(destination),
        ],
        check=True,
        env=environment,
    )
    subprocess.run(["pg_restore", "--list", str(destination)], check=True)
    return destination


def upload_backup(path: Path) -> str | None:
    bucket = os.getenv("S3_BACKUP_BUCKET", "")
    endpoint = os.getenv("S3_BACKUP_ENDPOINT", "")
    if not bucket or not endpoint:
        return None
    prefix = os.getenv("S3_BACKUP_PREFIX", "utilitaria/postgres").strip("/")
    key = f"{prefix}/{path.name}"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["S3_BACKUP_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_BACKUP_SECRET_ACCESS_KEY"],
        region_name=os.getenv("S3_BACKUP_REGION", "auto"),
    )
    client.upload_file(str(path), bucket, key)
    client.head_object(Bucket=bucket, Key=key)
    return key


def prune_local_backups():
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=max(2, int(os.getenv("BACKUP_LOCAL_RETENTION_DAYS", "7")))
    )
    for path in BACKUP_DIR.glob("utilitaria-*.dump"):
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            path.unlink()


async def main():
    interval = max(3600, int(os.getenv("BACKUP_INTERVAL_SECONDS", "86400")))
    while True:
        try:
            path = await asyncio.to_thread(create_backup)
            key = await asyncio.to_thread(upload_backup, path)
            await asyncio.to_thread(prune_local_backups)
            destination = key or f"local:{path} (S3 pendiente de configurar)"
            print(f"backup verified: {destination}", flush=True)
        except Exception as exc:
            print(f"backup failed: {exc}", flush=True)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
