"""Boundaries required by authentication use cases."""
from typing import Protocol, Mapping, Any

class AccountReader(Protocol):
    def find_for_login(self, email: str) -> Mapping[str, Any] | None: ...

class PasswordVerifier(Protocol):
    def verify(self, plain_password: str, stored_hash: str) -> bool: ...

class AccessTokenIssuer(Protocol):
    def issue(self, user_id: int) -> str: ...

class LoginRateLimiter(Protocol):
    def check(self, email: str) -> None: ...
