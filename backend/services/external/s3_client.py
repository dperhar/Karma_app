"""S3 client service for handling file uploads and storage."""

import uuid
from io import BytesIO

import boto3
from botocore.config import Config
from PIL import Image

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL,
)


class S3Client:
    """Client for S3 operations."""

    def __init__(self):
        """Initialize S3 client with credentials from environment."""
        self.bucket_name = S3_BUCKET_NAME
        self.base_url = S3_ENDPOINT_URL
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
            config=Config(signature_version="s3v4", connect_timeout=5, read_timeout=10),
        )

    async def upload_image_data(
        self,
        image_data: bytes,
        folder: str,
        image_size: tuple[int, int],
        thumb_size: tuple[int, int],
    ) -> dict[str, str]:
        """Upload image data to S3 with resized versions.

        Args:
            image_data: Raw image bytes to upload
            folder: Target folder in S3 bucket
            image_size: Tuple of (width, height) for main image
            thumb_size: Tuple of (width, height) for thumbnail

        Returns:
            Dictionary containing URLs for original, resized and thumbnail images

        Raises:
            ValueError: If image processing or upload fails
        """
        try:
            # Process image using PIL
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if needed
                if img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Generate unique filename
                filename = f"{uuid.uuid4()}.jpg"

                # Generate file paths
                original_key = f"{folder}/original/{filename}"
                image_key = f"{folder}/image/{filename}"
                thumb_key = f"{folder}/thumb/{filename}"

                # Save original image
                original_bytes = BytesIO()
                img.save(original_bytes, format="JPEG", quality=95)
                original_bytes.seek(0)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=original_key,
                    Body=original_bytes,
                    ContentType="image/jpeg",
                )

                # Process and upload main image
                main_img = img.copy()
                main_img.thumbnail(image_size, Image.Resampling.LANCZOS)
                main_bytes = BytesIO()
                main_img.save(main_bytes, format="JPEG", quality=85, optimize=True)
                main_bytes.seek(0)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=image_key,
                    Body=main_bytes,
                    ContentType="image/jpeg",
                )

                # Process and upload thumbnail
                thumb_img = img.copy()
                thumb_img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                thumb_bytes = BytesIO()
                thumb_img.save(thumb_bytes, format="JPEG", quality=85, optimize=True)
                thumb_bytes.seek(0)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=thumb_key,
                    Body=thumb_bytes,
                    ContentType="image/jpeg",
                )

                # Return URLs
                return {
                    "original_url": f"https://f25ac448-2962-4e49-9cb6-741deec66a61.selstorage.ru/{original_key}",
                    "image_url": f"https://f25ac448-2962-4e49-9cb6-741deec66a61.selstorage.ru/{image_key}",
                    "thumbnail_url": f"https://f25ac448-2962-4e49-9cb6-741deec66a61.selstorage.ru/{thumb_key}",
                }

        except Exception as e:
            raise ValueError(f"Error processing and uploading images: {e!s}") from e

    async def delete_image(self, image_path: str) -> None:
        """Delete an image and its variations from S3.

        Args:
            image_path: Path to the image in S3 (without variations)

        Raises:
            ValueError: If deletion fails
        """
        try:
            # Extract folder and filename
            folder = "/".join(image_path.split("/")[:-1])
            filename = image_path.split("/")[-1]

            # Delete all variations
            keys = [
                f"{folder}/original/{filename}",
                f"{folder}/image/{filename}",
                f"{folder}/thumb/{filename}",
            ]

            for key in keys:
                try:
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                except Exception:
                    # Continue deleting other variations even if one fails
                    continue

        except Exception as e:
            raise ValueError(f"Error deleting images: {e!s}") from e

    async def upload_image_with_resize(
        self,
        image_data: bytes,
        folder: str,
        image_size: tuple[int, int],
        thumb_size: tuple[int, int],
    ) -> dict[str, str]:
        """Upload image data to S3 with resized versions.

        Args:
            image_data: Raw image bytes
            folder: S3 folder to upload to
            image_size: Target size for main image (width, height)
            thumb_size: Target size for thumbnail (width, height)

        Returns:
            Dictionary with URLs for uploaded images
        """
        try:
            # Process image using PIL
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if needed
                if img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Generate unique filename
                filename = f"{uuid.uuid4()}.jpg"

                # Generate file paths
                original_key = f"{folder}/original/{filename}"
                image_key = f"{folder}/image/{filename}"
                thumb_key = f"{folder}/thumb/{filename}"

                # Save original image
                original_bytes = BytesIO()
                img.save(original_bytes, format="JPEG", quality=95)
                original_bytes.seek(0)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=original_key,
                    Body=original_bytes,
                    ContentType="image/jpeg",
                )

                # Process and upload main image
                main_img = img.copy()
                main_img.thumbnail(image_size, Image.Resampling.LANCZOS)
                main_bytes = BytesIO()
                main_img.save(main_bytes, format="JPEG", quality=85, optimize=True)
                main_bytes.seek(0)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=image_key,
                    Body=main_bytes,
                    ContentType="image/jpeg",
                )

                # Process and upload thumbnail
                thumb_img = img.copy()
                thumb_img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                thumb_bytes = BytesIO()
                thumb_img.save(thumb_bytes, format="JPEG", quality=85, optimize=True)
                thumb_bytes.seek(0)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=thumb_key,
                    Body=thumb_bytes,
                    ContentType="image/jpeg",
                )

                # Return URLs
                return {
                    "original_url": f"https://f25ac448-2962-4e49-9cb6-741deec66a61.selstorage.ru/{original_key}",
                    "image_url": f"https://f25ac448-2962-4e49-9cb6-741deec66a61.selstorage.ru/{image_key}",
                    "thumbnail_url": f"https://f25ac448-2962-4e49-9cb6-741deec66a61.selstorage.ru/{thumb_key}",
                }

        except Exception as e:
            raise ValueError(f"Error processing and uploading images: {e!s}") from e
