import logging
from abc import abstractmethod, ABC
from json import loads
from typing import Optional

import boto3
from botocore.client import Config, ClientError
from pylon.core.tools import log

from .constants import MINIO_ACCESS, MINIO_ENDPOINT, MINIO_SECRET, MINIO_REGION
from .rpc_tools import RpcMixin


class MinioClientABC(ABC):
    PROJECT_SECRET_KEY: str = "minio_aws_access"

    def __init__(self,
                 aws_access_key_id: str = MINIO_ACCESS,
                 aws_secret_access_key: str = MINIO_SECRET,
                 logger: Optional[logging.Logger] = None
                 ):
        self._logger = logger or logging.getLogger(self.__class__.__name__.lower())
        self.s3_client = boto3.client(
            "s3", endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name=MINIO_REGION
        )

    @property
    @abstractmethod
    def bucket_prefix(self) -> str:
        raise NotImplementedError

    def format_bucket_name(self, bucket: str) -> str:
        if bucket.startswith(self.bucket_prefix):
            return bucket
        return f"{self.bucket_prefix}{bucket}"

    def list_bucket(self) -> list:
        return [
            each["Name"].replace(self.bucket_prefix, "", 1)
            for each in self.s3_client.list_buckets().get("Buckets", {})
            if each["Name"].startswith(self.bucket_prefix)
        ]

    def create_bucket(self, bucket: str, bucket_type=None) -> dict:
        try:
            response = self.s3_client.create_bucket(
                ACL="public-read",
                Bucket=self.format_bucket_name(bucket),
                CreateBucketConfiguration={"LocationConstraint": MINIO_REGION}
            )
            if bucket_type and bucket_type in ('system', 'autogenerated', 'local'):
                self.set_bucket_tags(bucket=bucket, tags={'type': bucket_type})
            return response
        except ClientError as client_error:
            self._logger.warning(str(client_error))
            return str(client_error)
        except Exception as exc:
            self._logger.error(str(exc))
            return str(exc)

    def list_files(self, bucket: str) -> list:
        response = self.s3_client.list_objects_v2(Bucket=self.format_bucket_name(bucket))
        files = [
            {
                "name": each["Key"], "size": each["Size"],
                "modified": each["LastModified"].isoformat()
            }
            for each in response.get("Contents", {})
        ]
        continuation_token = response.get("NextContinuationToken")
        while continuation_token and response["Contents"]:
            response = self.s3_client.list_objects_v2(Bucket=self.format_bucket_name(bucket),
                                                      ContinuationToken=continuation_token)
            appendage = [
                {
                    "name": each["Key"],
                    "size": each["Size"],
                    "modified": each["LastModified"].isoformat()
                }
                for each in response.get("Contents", {})
            ]
            if not appendage:
                break
            files += appendage
            continuation_token = response.get("NextContinuationToken")
        return files

    def upload_file(self, bucket: str, file_obj: bytes, file_name: str):
        return self.s3_client.put_object(Key=file_name, Bucket=self.format_bucket_name(bucket), Body=file_obj)

    def download_file(self, bucket: str, file_name: str):
        return self.s3_client.get_object(Bucket=self.format_bucket_name(bucket), Key=file_name)["Body"].read()

    def remove_file(self, bucket: str, file_name: str):
        return self.s3_client.delete_object(Bucket=self.format_bucket_name(bucket), Key=file_name)

    def remove_bucket(self, bucket: str):
        for file_obj in self.list_files(bucket):
            self.remove_file(bucket, file_obj["name"])

        self.s3_client.delete_bucket(Bucket=self.format_bucket_name(bucket))

    def configure_bucket_lifecycle(self, bucket: str, days: int) -> None:
        self.s3_client.put_bucket_lifecycle_configuration(
            Bucket=self.format_bucket_name(bucket),
            LifecycleConfiguration={
                "Rules": [
                    {
                        "Expiration": {
                            # "NoncurrentVersionExpiration": days,
                            "Days": days
                            # "ExpiredObjectDeleteMarker": True
                        },
                        "NoncurrentVersionExpiration": {
                            'NoncurrentDays': days
                        },
                        "ID": "bucket-retention-policy",
                        'Filter': {'Prefix': ''},
                        "Status": "Enabled"
                    }
                ]
            }
        )

    def get_bucket_lifecycle(self, bucket: str) -> dict:
        return self.s3_client.get_bucket_lifecycle(Bucket=self.format_bucket_name(bucket))

    def get_bucket_size(self, bucket: str) -> int:
        total_size = 0
        for each in self.s3_client.list_objects_v2(
                Bucket=self.format_bucket_name(bucket)
        ).get('Contents', {}):
            total_size += each["Size"]
        return total_size

    def get_file_size(self, bucket: str, filename: str) -> int:
        response = self.s3_client.list_objects_v2(Bucket=self.format_bucket_name(bucket)).get("Contents", {})

        file_size = 0
        for each in response:
            if str(each["Key"]).lower() == str(filename).lower():
                file_size += each["Size"]
                break

        return file_size

    def get_bucket_tags(self, bucket: str) -> dict:
        try:
            return self.s3_client.get_bucket_tagging(Bucket=self.format_bucket_name(bucket))
        except ClientError:
            return {}

    def set_bucket_tags(self, bucket: str, tags: dict) -> None:
        tag_set = [{'Key': k, 'Value': v} for k, v in tags.items()]
        self.s3_client.put_bucket_tagging(
            Bucket=self.format_bucket_name(bucket),
            Tagging={
                'TagSet': tag_set
            },
        )

    def select_object_content(self, bucket: str, file_name: str, expression_addon: str = '') -> list:
        try:
            response = self.s3_client.select_object_content(
                Bucket=bucket,
                Key=file_name,
                ExpressionType='SQL',
                Expression=f"select * from s3object s{expression_addon}",
                InputSerialization={
                    'CSV': {
                        "FileHeaderInfo": "USE",
                    },
                    'CompressionType': 'GZIP',
                },
                OutputSerialization={'JSON': {}},
            )
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'NoSuchKey':
                log.error(f'Cannot find file "{file_name}" in bucket "{bucket}"')
                return []
            else:
                raise
        results = []
        for event in response['Payload']:
            if 'Records' in event:
                payload = event['Records']['Payload'].decode('utf-8')
                for line in payload.split('\n'):
                    try:
                        results.append(loads(line))
                    except Exception:
                        pass
        return results

    def is_file_exist(self, bucket: str, file_name: str):
        response = self.s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=file_name,
        )
        for obj in response.get('Contents', []):
            if obj['Key'] == file_name:
                return True
        return False


class MinioClientAdmin(MinioClientABC):
    @property
    def bucket_prefix(self) -> str:
        return 'p--administration.'


class MinioClient(MinioClientABC):
    @classmethod
    def from_project_id(cls, project_id: int, logger: Optional[logging.Logger] = None, rpc_manager=None):
        if not rpc_manager:
            rpc_manager = RpcMixin().rpc
        project = rpc_manager.call.project_get_or_404(project_id=project_id)
        return cls(project, logger)

    def __init__(self, project, logger: Optional[logging.Logger] = None):
        self.project = project
        aws_access_key_id, aws_secret_access_key = self.extract_access_data()
        super().__init__(aws_access_key_id, aws_secret_access_key, logger)

    def extract_access_data(self) -> tuple:
        if self.project and self.PROJECT_SECRET_KEY in (self.project.secrets_json or {}):
            aws_access_json = self.project.secrets_json[self.PROJECT_SECRET_KEY]
            aws_access_key_id = aws_access_json.get("aws_access_key_id")
            aws_secret_access_key = aws_access_json.get("aws_secret_access_key")
            return aws_access_key_id, aws_secret_access_key
        return MINIO_ACCESS, MINIO_SECRET

    @property
    def bucket_prefix(self) -> str:
        return f'p--{self.project.id}.'
