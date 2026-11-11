"""Authentication rules without HTTP, persistence or token libraries."""

class InvalidCredentials(ValueError):
    pass

class BannedAccount(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.lower()


def authenticate(user, password: str, password_verifier):
    """Avoid leaking whether the supplied email is registered."""
    if user is None or not password_verifier(password, user['pw_hash']):
        raise InvalidCredentials('Неверный email или пароль')
    if user['banned_at']:
        raise BannedAccount('Аккаунт заблокирован модератором')
    return user['id']
