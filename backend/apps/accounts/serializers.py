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


class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for User details"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class ClientSerializer(serializers.ModelSerializer):
    """Serializer for Client model - for list/retrieve"""
    profile = ProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='profile.user.email', read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'profile', 'full_name', 'email', 'is_student',
            'emergency_contact', 'emergency_phone', 'medical_notes'
        ]
        read_only_fields = ['id']

    def get_full_name(self, obj):
        """Get client's full name"""
        return obj.profile.user.get_full_name() or obj.profile.user.username


class ClientCreateSerializer(serializers.Serializer):
    """Serializer for creating a new client (admin only)"""
    # User fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    # Profile fields
    phone = serializers.CharField(max_length=17)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True)

    # Client fields
    is_student = serializers.BooleanField(default=False)
    emergency_contact = serializers.CharField(max_length=100, required=False, allow_blank=True)
    emergency_phone = serializers.CharField(max_length=17, required=False, allow_blank=True)
    medical_notes = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        """Check if username already exists"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким username уже существует")
        return value

    def validate_phone(self, value):
        """Check if phone already exists"""
        if Profile.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Пользователь с таким телефоном уже существует")
        return value

    def create(self, validated_data):
        """Create User, Profile and Client"""
        from django.db import transaction

        # Extract data for different models
        user_data = {
            'username': validated_data['username'],
            'email': validated_data['email'],
            'first_name': validated_data.get('first_name', ''),
            'last_name': validated_data.get('last_name', ''),
        }
        password = validated_data['password']

        profile_data = {
            'phone': validated_data['phone'],
            'date_of_birth': validated_data.get('date_of_birth'),
            'address': validated_data.get('address', ''),
            'role': UserRole.CLIENT,
        }

        client_data = {
            'is_student': validated_data.get('is_student', False),
            'emergency_contact': validated_data.get('emergency_contact', ''),
            'emergency_phone': validated_data.get('emergency_phone', ''),
            'medical_notes': validated_data.get('medical_notes', ''),
        }

        # Create all objects in transaction
        with transaction.atomic():
            # Create User
            user = User.objects.create_user(password=password, **user_data)

            # Create Profile
            profile = Profile.objects.create(user=user, **profile_data)

            # Create Client
            client = Client.objects.create(profile=profile, **client_data)

        return client

    def to_representation(self, instance):
        """Use ClientSerializer for output representation"""
        return ClientSerializer(instance).data


class ClientUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating client information"""
    # User fields (editable)
    email = serializers.EmailField(source='profile.user.email')
    first_name = serializers.CharField(source='profile.user.first_name', required=False)
    last_name = serializers.CharField(source='profile.user.last_name', required=False)

    # Profile fields (editable)
    phone = serializers.CharField(source='profile.phone')
    date_of_birth = serializers.DateField(source='profile.date_of_birth', required=False, allow_null=True)
    address = serializers.CharField(source='profile.address', required=False, allow_blank=True)

    class Meta:
        model = Client
        fields = [
            'email', 'first_name', 'last_name', 'phone',
            'date_of_birth', 'address', 'is_student',
            'emergency_contact', 'emergency_phone', 'medical_notes'
        ]

    def update(self, instance, validated_data):
        """Update User, Profile and Client"""
        from django.db import transaction

        with transaction.atomic():
            # Update User fields
            if 'profile' in validated_data and 'user' in validated_data['profile']:
                user_data = validated_data['profile'].pop('user')
                user = instance.profile.user
                for attr, value in user_data.items():
                    setattr(user, attr, value)
                user.save()

            # Update Profile fields
            if 'profile' in validated_data:
                profile_data = validated_data.pop('profile')
                profile = instance.profile
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()

            # Update Client fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

        return instance


class TrainerSerializer(serializers.ModelSerializer):
    """Serializer for Trainer model"""
    profile = ProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Trainer
        fields = [
            'id', 'profile', 'full_name', 'specialization',
            'experience_years', 'bio', 'certifications', 'is_active'
        ]
        read_only_fields = ['id']

    def get_full_name(self, obj):
        """Get trainer's full name"""
        return obj.profile.user.get_full_name() or obj.profile.user.username
