from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class StudentAwareTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        if hasattr(user, 'student') and not user.student.can_login:
            token.delete()
            raise AuthenticationFailed('当前账号已被禁止登录，请联系管理员。')

        return user, token
