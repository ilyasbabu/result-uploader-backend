from rest_framework import serializers



class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(required=True, allow_blank=False)


class StudentCreateSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False)
    registration_no = serializers.CharField(required=True, allow_blank=False)
    course = serializers.CharField(required=True, allow_blank=False)