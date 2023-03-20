from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

from .models import UserAuthToken


class CustomTokenAuthentication(TokenAuthentication):
    model = UserAuthToken

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = (
                model.objects.select_related("user")
                .filter(key=key, is_active=True, is_expired=False)
                .order_by("-created_time")
            )
            if not token.exists():
                raise exceptions.ValidationError(("Invalid token."))
            token = token[0]
        except model.DoesNotExist:
            raise exceptions.ValidationError(("Invalid token."))
        if not token.is_active:
            raise exceptions.ValidationError(("User inactive or deleted."))
        if not token.user.is_active:
            raise exceptions.ValidationError(("User inactive or deleted."))

        return (token.user, token)