
from tortoise import fields, models
from uuid import uuid4

class OAuthClient(models.Model):
    id = fields.UUIDField(pk=True)
    client_id = fields.CharField(max_length=255, unique=True, index=True)
    client_secret = fields.CharField(max_length=255)
    client_name = fields.CharField(max_length=255)
    client_description = fields.CharField(max_length=255, null=True)
    redirect_uri = fields.TextField(null=False)
    login_url = fields.TextField(null=True)
    consent_url = fields.TextField(null=True)
    scopes = fields.JSONField(nullable=False) 
    grant_types = fields.JSONField(nullable=False)
    public_client = fields.BooleanField(default=True, index=True)
    allowed_user_types = fields.JSONField(null=True)
    allowlist_enabled = fields.BooleanField(default=False, index=True)
    is_active = fields.BooleanField(default=True, index=True)
    created_by = fields.UUIDField(null=False, index=True)
    updated_by = fields.UUIDField(null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "oauth_clients"
        ordering = ["-created_at"]


class OAuthClientBlock(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    client = fields.ForeignKeyField("models.OAuthClient", related_name="blocked_entries", on_delete=fields.CASCADE)
    user_id = fields.UUIDField(null=False, index=True)
    user_type = fields.CharField(max_length=50, null=False, index=True)
    citizen_id = fields.CharField(max_length=20, null=True, index=True)
    full_name = fields.CharField(max_length=255, null=True)
    note = fields.CharField(max_length=255, null=True)
    created_by = fields.UUIDField(null=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "oauth_client_blocks"
        unique_together = (("client", "user_id", "user_type"),)
        ordering = ["-created_at"]


class OAuthClientAllow(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    client = fields.ForeignKeyField("models.OAuthClient", related_name="allowed_entries", on_delete=fields.CASCADE)
    user_id = fields.UUIDField(null=False, index=True)
    user_type = fields.CharField(max_length=50, null=False, index=True)
    citizen_id = fields.CharField(max_length=20, null=True, index=True)
    full_name = fields.CharField(max_length=255, null=True)
    note = fields.CharField(max_length=255, null=True)
    created_by = fields.UUIDField(null=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "oauth_client_allows"
        unique_together = (("client", "user_id", "user_type"),)
        ordering = ["-created_at"]


class OAuthClientUserTypeDefault(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    client = fields.OneToOneField("models.OAuthClient", related_name="user_type_default", on_delete=fields.CASCADE)
    allowed_user_types = fields.JSONField(null=True)
    created_by = fields.UUIDField(null=True)
    updated_by = fields.UUIDField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "oauth_client_user_type_defaults"
        ordering = ["-updated_at"]


class OAuthConsent(models.Model):
    id = fields.UUIDField(pk=True)
    user_id = fields.UUIDField(null=False, index=True)
    client_id = fields.CharField(max_length=255, null=False, index=True)
    scopes = fields.JSONField(nullable=False)
    accepted_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "oauth_consents"
        ordering = ["-accepted_at"]
        unique_together = [("user_id", "client_id")]

class OAuthAuthorizationCode(models.Model):
    id = fields.UUIDField(pk=True)
    code = fields.CharField(max_length=255, unique=True, index=True)
    user_id = fields.UUIDField(null=False, index=True)
    user_type = fields.CharField(max_length=255, null=False, index=True)
    # allow multiple codes per client; uniqueness ensured on code
    client_id = fields.CharField(max_length=255, index=True)
    scopes = fields.JSONField(nullable=False)
    # PKCE support
    code_challenge = fields.CharField(max_length=255, null=True)
    code_challenge_method = fields.CharField(max_length=10, null=True)
    # OIDC nonce binding
    nonce = fields.CharField(max_length=255, null=True)
    expires_at = fields.DatetimeField(null=False)

    class Meta:
        table = "oauth_authorization_codes"
        ordering = ["-expires_at"]

class RefreshToken(models.Model):
    id = fields.UUIDField(pk=True, default=uuid4)
    token = fields.CharField(max_length=1000, unique=True, index=True) 
    user_id = fields.UUIDField(null=False, index=True)
    user_type = fields.CharField(max_length=255, null=True, index=True)
    client_id = fields.CharField(max_length=255, null=False, index=True)
    scopes = fields.JSONField(nullable=False)
    expires_at = fields.DatetimeField(null=False)
    is_revoked = fields.BooleanField(default=False, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "refresh_tokens"
        ordering = ["-created_at"]
