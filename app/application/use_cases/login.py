"""Authentication orchestration, independently unit-testable."""
from app.application.ports.auth import AccountReader, PasswordVerifier, AccessTokenIssuer, LoginRateLimiter
from app.domain.services.auth import authenticate, normalize_email

class LoginUser:
    def __init__(self, accounts: AccountReader, passwords: PasswordVerifier,
                 tokens: AccessTokenIssuer, rate_limit: LoginRateLimiter):
        self.accounts = accounts
        self.passwords = passwords
        self.tokens = tokens
        self.rate_limit = rate_limit

    def execute(self, email: str, password: str) -> dict:
        email = normalize_email(email)
        self.rate_limit.check(email)
        user = self.accounts.find_for_login(email)
        user_id = authenticate(user, password, self.passwords.verify)
        return {'token': self.tokens.issue(user_id)}
