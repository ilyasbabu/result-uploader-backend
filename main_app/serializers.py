from rest_framework import serializers



class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(required=True, allow_blank=False)


class StudentCreateSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False)
    name = serializers.CharField(required=True, allow_blank=False)
    registration_no = serializers.CharField(required=True, allow_blank=False)


class StudentListSerialzer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    registration_no = serializers.CharField()

    def get_name(self, obj):
        return obj.user.first_name
    

class MarksViewRequestSerialzerFaculty(serializers.Serializer):
    student = serializers.IntegerField(required=True)
    exam = serializers.IntegerField(required=True)


class MarksViewRequestSerialzerStudent(serializers.Serializer):
    exam = serializers.IntegerField(required=True)


class MarksViewSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    grade = serializers.CharField()
    grade_point = serializers.IntegerField()
    credit = serializers.IntegerField()
    credit_point = serializers.IntegerField()
    status = serializers.CharField()
    subject_code = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()

    def get_subject_code(self, obj):
        return obj.subject.subject_code
    
    def get_subject_name(self, obj):
        return obj.subject.subject_name
