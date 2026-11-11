"""Production implementations of password and token ports."""
from app.security import check_pw, make_token
from app.cache import hit

class ScryptPasswordVerifier:
    def verify(self, plain_password: str, stored_hash: str) -> bool:
        return check_pw(plain_password, stored_hash)

class JwtAccessTokenIssuer:
    def issue(self, user_id: int) -> str:
        return make_token(user_id)

class RedisLoginRateLimiter:
    def check(self, email: str) -> None:
        hit('login-email', email, 10, 900)
