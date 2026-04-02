from uuid import uuid4
from tortoise import fields, models


class NewsArticle(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    title = fields.CharField(max_length=255, index=True)
    department = fields.CharField(max_length=255, index=True)
    content_html = fields.TextField()
    image_urls = fields.JSONField(default=list)
    platforms = fields.JSONField(default=list)  # List of platforms: ["SmartOSM", "ThaiPHC"]

    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)

    created_at = fields.DatetimeField(auto_now_add=True, index=True)
    updated_at = fields.DatetimeField(auto_now=True, index=True)
    deleted_at = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "news_articles"
