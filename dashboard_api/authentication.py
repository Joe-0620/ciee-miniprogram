from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import DashboardLoginSession


class DashboardSessionAuthentication(BaseAuthentication):
    keyword = 'Token'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth:
            return None

        if auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            raise AuthenticationFailed('Invalid token header. No credentials provided.')
        if len(auth) > 2:
            raise AuthenticationFailed('Invalid token header. Token string should not contain spaces.')

        try:
            key = auth[1].decode()
        except UnicodeError as exc:
            raise AuthenticationFailed('Invalid token header. Token string should not contain invalid characters.') from exc

        session = DashboardLoginSession.objects.select_related('user').filter(key=key, is_active=True).first()
        if not session:
            raise AuthenticationFailed('Invalid token.')

        user = session.user
        if not user or not user.is_active or not user.is_staff:
            raise AuthenticationFailed('User inactive or unauthorized.')

        session.touch()
        return (user, session)
