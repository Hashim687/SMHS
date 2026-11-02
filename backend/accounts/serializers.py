from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "staff_id", "phone",
                  "language", "is_active", "totp_enabled", "password"]
        read_only_fields = ["totp_enabled"]

    def validate_password(self, v):
        validate_password(v)
        return v

    def create(self, data):
        pw = data.pop("password", None)
        if not pw:
            raise serializers.ValidationError({"password": "required"})
        u = User(**data)
        u.set_password(pw)
        u.save()
        return u

    def update(self, inst, data):
        pw = data.pop("password", None)
        for k, v in data.items():
            setattr(inst, k, v)
        if pw:
            inst.set_password(pw)
        inst.save()
        return inst


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128)


class OtpSerializer(serializers.Serializer):
    mfa_token = serializers.CharField()
    code = serializers.RegexField(r"^\d{6}$")
