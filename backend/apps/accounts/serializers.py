"""
Serializers for accounts app
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Profile, Client, Trainer, UserRole


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    phone = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name', 'phone')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        # Remove password2 and phone as they're not User fields
        validated_data.pop('password2')
        phone = validated_data.pop('phone')

        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password']
        )

        # Create profile
        profile = Profile.objects.create(
            user=user,
            phone=phone,
            role=UserRole.CLIENT
        )

        # Create client info
        Client.objects.create(profile=profile)

        return user


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile
    """
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')

    class Meta:
        model = Profile
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role',
                  'phone', 'date_of_birth', 'photo', 'address', 'created_at')
        read_only_fields = ('id', 'username', 'role', 'created_at')
