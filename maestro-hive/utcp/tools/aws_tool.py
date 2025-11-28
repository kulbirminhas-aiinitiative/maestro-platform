"""
UTCP AWS Integration Tool

Provides AWS integration for AI agents:
- S3 operations (upload, download, list)
- Lambda invocations
- SQS messaging
- DynamoDB operations
- CloudWatch logs

Part of MD-424: Build AWS Integration Adapter
"""

import json
import hashlib
import hmac
from datetime import datetime
from typing import Any, Dict, List, Optional
import aiohttp
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class AWSTool(UTCPTool):
    """AWS integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="aws",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.DELETE,
                ToolCapability.EXECUTE,
            ],
            required_credentials=["aws_access_key_id", "aws_secret_access_key", "aws_region"],
            optional_credentials=["aws_session_token"],
            rate_limit=None,
            timeout=60,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.access_key = credentials["aws_access_key_id"]
        self.secret_key = credentials["aws_secret_access_key"]
        self.region = credentials["aws_region"]
        self.session_token = credentials.get("aws_session_token")

    def _sign_request(
        self,
        method: str,
        service: str,
        host: str,
        uri: str,
        headers: Dict[str, str],
        payload: str = "",
    ) -> Dict[str, str]:
        """Sign request using AWS Signature Version 4."""
        t = datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')

        # Create canonical request
        canonical_headers = ""
        signed_headers = ""
        header_list = sorted(headers.keys())
        for key in header_list:
            canonical_headers += f"{key.lower()}:{headers[key]}\n"
            signed_headers += f"{key.lower()};"
        signed_headers = signed_headers[:-1]

        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        canonical_request = f"{method}\n{uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f"{date_stamp}/{self.region}/{service}/aws4_request"
        string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

        # Calculate signature
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        k_date = sign(('AWS4' + self.secret_key).encode('utf-8'), date_stamp)
        k_region = sign(k_date, self.region)
        k_service = sign(k_region, service)
        k_signing = sign(k_service, 'aws4_request')
        signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        # Create authorization header
        authorization = f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

        headers['Authorization'] = authorization
        headers['x-amz-date'] = amz_date
        headers['x-amz-content-sha256'] = payload_hash

        if self.session_token:
            headers['x-amz-security-token'] = self.session_token

        return headers

    async def health_check(self) -> ToolResult:
        """Check AWS connectivity by listing S3 buckets."""
        try:
            result = await self.s3_list_buckets()
            if result.success:
                return ToolResult.ok({
                    "connected": True,
                    "region": self.region,
                    "buckets_accessible": True,
                })
            else:
                return result
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    # =========================================================================
    # S3 Operations
    # =========================================================================

    async def s3_list_buckets(self) -> ToolResult:
        """List all S3 buckets."""
        try:
            host = "s3.amazonaws.com"
            headers = {"Host": host}
            headers = self._sign_request("GET", "s3", host, "/", headers)

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://{host}/", headers=headers) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise ToolError(f"S3 error: {text}", code=f"S3_{response.status}")

                    text = await response.text()
                    # Simple XML parsing for bucket names
                    buckets = []
                    import re
                    for match in re.finditer(r'<Name>([^<]+)</Name>', text):
                        buckets.append(match.group(1))

                    return ToolResult.ok({"buckets": buckets})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="S3_LIST_BUCKETS_FAILED")

    async def s3_list_objects(
        self,
        bucket: str,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> ToolResult:
        """
        List objects in an S3 bucket.

        Args:
            bucket: Bucket name
            prefix: Object prefix filter
            max_keys: Maximum number of keys

        Returns:
            ToolResult with object list
        """
        try:
            host = f"{bucket}.s3.{self.region}.amazonaws.com"
            uri = f"/?list-type=2&prefix={prefix}&max-keys={max_keys}"
            headers = {"Host": host}
            headers = self._sign_request("GET", "s3", host, uri, headers)

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://{host}{uri}", headers=headers) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise ToolError(f"S3 error: {text}", code=f"S3_{response.status}")

                    text = await response.text()
                    # Simple XML parsing
                    objects = []
                    import re
                    for match in re.finditer(r'<Key>([^<]+)</Key>', text):
                        objects.append(match.group(1))

                    return ToolResult.ok({"objects": objects, "bucket": bucket})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="S3_LIST_OBJECTS_FAILED")

    async def s3_get_object(self, bucket: str, key: str) -> ToolResult:
        """
        Get an object from S3.

        Args:
            bucket: Bucket name
            key: Object key

        Returns:
            ToolResult with object content
        """
        try:
            host = f"{bucket}.s3.{self.region}.amazonaws.com"
            uri = f"/{key}"
            headers = {"Host": host}
            headers = self._sign_request("GET", "s3", host, uri, headers)

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://{host}{uri}", headers=headers) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise ToolError(f"S3 error: {text}", code=f"S3_{response.status}")

                    content = await response.read()
                    content_type = response.headers.get("Content-Type", "application/octet-stream")

                    # Try to decode as text if possible
                    try:
                        body = content.decode('utf-8')
                    except:
                        body = content.hex()

                    return ToolResult.ok({
                        "key": key,
                        "content_type": content_type,
                        "size": len(content),
                        "body": body,
                    })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="S3_GET_OBJECT_FAILED")

    async def s3_put_object(
        self,
        bucket: str,
        key: str,
        body: str,
        content_type: str = "text/plain",
    ) -> ToolResult:
        """
        Put an object to S3.

        Args:
            bucket: Bucket name
            key: Object key
            body: Object content
            content_type: Content type

        Returns:
            ToolResult with upload status
        """
        try:
            host = f"{bucket}.s3.{self.region}.amazonaws.com"
            uri = f"/{key}"
            headers = {
                "Host": host,
                "Content-Type": content_type,
            }
            headers = self._sign_request("PUT", "s3", host, uri, headers, body)

            async with aiohttp.ClientSession() as session:
                async with session.put(f"https://{host}{uri}", headers=headers, data=body) as response:
                    if response.status not in [200, 201]:
                        text = await response.text()
                        raise ToolError(f"S3 error: {text}", code=f"S3_{response.status}")

                    etag = response.headers.get("ETag", "").strip('"')

                    return ToolResult.ok({
                        "uploaded": True,
                        "bucket": bucket,
                        "key": key,
                        "etag": etag,
                    })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="S3_PUT_OBJECT_FAILED")

    async def s3_delete_object(self, bucket: str, key: str) -> ToolResult:
        """
        Delete an object from S3.

        Args:
            bucket: Bucket name
            key: Object key

        Returns:
            ToolResult with deletion status
        """
        try:
            host = f"{bucket}.s3.{self.region}.amazonaws.com"
            uri = f"/{key}"
            headers = {"Host": host}
            headers = self._sign_request("DELETE", "s3", host, uri, headers)

            async with aiohttp.ClientSession() as session:
                async with session.delete(f"https://{host}{uri}", headers=headers) as response:
                    if response.status not in [200, 204]:
                        text = await response.text()
                        raise ToolError(f"S3 error: {text}", code=f"S3_{response.status}")

                    return ToolResult.ok({
                        "deleted": True,
                        "bucket": bucket,
                        "key": key,
                    })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="S3_DELETE_OBJECT_FAILED")

    # =========================================================================
    # Lambda Operations
    # =========================================================================

    async def lambda_invoke(
        self,
        function_name: str,
        payload: Optional[Dict] = None,
        invocation_type: str = "RequestResponse",
    ) -> ToolResult:
        """
        Invoke a Lambda function.

        Args:
            function_name: Function name or ARN
            payload: Input payload
            invocation_type: 'RequestResponse', 'Event', or 'DryRun'

        Returns:
            ToolResult with function response
        """
        try:
            host = f"lambda.{self.region}.amazonaws.com"
            uri = f"/2015-03-31/functions/{function_name}/invocations"
            body = json.dumps(payload or {})

            headers = {
                "Host": host,
                "Content-Type": "application/json",
                "X-Amz-Invocation-Type": invocation_type,
            }
            headers = self._sign_request("POST", "lambda", host, uri, headers, body)

            async with aiohttp.ClientSession() as session:
                async with session.post(f"https://{host}{uri}", headers=headers, data=body) as response:
                    if response.status >= 400:
                        text = await response.text()
                        raise ToolError(f"Lambda error: {text}", code=f"LAMBDA_{response.status}")

                    result_body = await response.text()
                    function_error = response.headers.get("X-Amz-Function-Error")

                    try:
                        result_data = json.loads(result_body) if result_body else None
                    except:
                        result_data = result_body

                    return ToolResult.ok({
                        "invoked": True,
                        "function_name": function_name,
                        "status_code": response.status,
                        "function_error": function_error,
                        "payload": result_data,
                    })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LAMBDA_INVOKE_FAILED")

    # =========================================================================
    # SQS Operations
    # =========================================================================

    async def sqs_send_message(
        self,
        queue_url: str,
        message_body: str,
        delay_seconds: int = 0,
        message_attributes: Optional[Dict] = None,
    ) -> ToolResult:
        """
        Send a message to an SQS queue.

        Args:
            queue_url: Queue URL
            message_body: Message content
            delay_seconds: Delay before message is available
            message_attributes: Optional message attributes

        Returns:
            ToolResult with message ID
        """
        try:
            # Parse queue URL to get host
            from urllib.parse import urlparse
            parsed = urlparse(queue_url)
            host = parsed.netloc
            uri = parsed.path

            body = f"Action=SendMessage&MessageBody={message_body}&DelaySeconds={delay_seconds}"

            headers = {
                "Host": host,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            headers = self._sign_request("POST", "sqs", host, uri, headers, body)

            async with aiohttp.ClientSession() as session:
                async with session.post(f"https://{host}{uri}", headers=headers, data=body) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise ToolError(f"SQS error: {text}", code=f"SQS_{response.status}")

                    text = await response.text()
                    # Parse MessageId from XML
                    import re
                    match = re.search(r'<MessageId>([^<]+)</MessageId>', text)
                    message_id = match.group(1) if match else None

                    return ToolResult.ok({
                        "sent": True,
                        "message_id": message_id,
                    })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SQS_SEND_FAILED")

    async def sqs_receive_messages(
        self,
        queue_url: str,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
    ) -> ToolResult:
        """
        Receive messages from an SQS queue.

        Args:
            queue_url: Queue URL
            max_messages: Maximum number of messages (1-10)
            wait_time_seconds: Long polling duration

        Returns:
            ToolResult with messages
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(queue_url)
            host = parsed.netloc
            uri = parsed.path

            body = f"Action=ReceiveMessage&MaxNumberOfMessages={max_messages}&WaitTimeSeconds={wait_time_seconds}"

            headers = {
                "Host": host,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            headers = self._sign_request("POST", "sqs", host, uri, headers, body)

            async with aiohttp.ClientSession() as session:
                async with session.post(f"https://{host}{uri}", headers=headers, data=body) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise ToolError(f"SQS error: {text}", code=f"SQS_{response.status}")

                    text = await response.text()
                    # Simple XML parsing for messages
                    messages = []
                    import re
                    for msg_match in re.finditer(r'<Message>(.*?)</Message>', text, re.DOTALL):
                        msg_xml = msg_match.group(1)
                        msg_id = re.search(r'<MessageId>([^<]+)</MessageId>', msg_xml)
                        body = re.search(r'<Body>([^<]+)</Body>', msg_xml)
                        receipt = re.search(r'<ReceiptHandle>([^<]+)</ReceiptHandle>', msg_xml)

                        messages.append({
                            "message_id": msg_id.group(1) if msg_id else None,
                            "body": body.group(1) if body else None,
                            "receipt_handle": receipt.group(1) if receipt else None,
                        })

                    return ToolResult.ok({"messages": messages})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SQS_RECEIVE_FAILED")

    # =========================================================================
    # Secrets Manager Operations
    # =========================================================================

    async def secrets_get_secret(self, secret_id: str) -> ToolResult:
        """
        Get a secret from Secrets Manager.

        Args:
            secret_id: Secret name or ARN

        Returns:
            ToolResult with secret value
        """
        try:
            host = f"secretsmanager.{self.region}.amazonaws.com"
            uri = "/"
            body = json.dumps({"SecretId": secret_id})

            headers = {
                "Host": host,
                "Content-Type": "application/x-amz-json-1.1",
                "X-Amz-Target": "secretsmanager.GetSecretValue",
            }
            headers = self._sign_request("POST", "secretsmanager", host, uri, headers, body)

            async with aiohttp.ClientSession() as session:
                async with session.post(f"https://{host}{uri}", headers=headers, data=body) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise ToolError(f"Secrets Manager error: {text}", code=f"SM_{response.status}")

                    result = await response.json()

                    return ToolResult.ok({
                        "name": result.get("Name"),
                        "secret_string": result.get("SecretString"),
                        "version_id": result.get("VersionId"),
                    })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SECRETS_GET_FAILED")
