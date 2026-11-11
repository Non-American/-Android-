"""Composition root: connects application ports to concrete implementations."""
from app.application.use_cases.login import LoginUser
from app.application.use_cases.profile import ProfileUseCases
from app.infrastructure.repositories.login import PostgresAccountReader
from app.infrastructure.repositories.profile import PostgresProfileWriter
from app.infrastructure.security.login import (ScryptPasswordVerifier,
    JwtAccessTokenIssuer, RedisLoginRateLimiter)
from app import embeddings, cache


def login_use_case() -> LoginUser:
    return LoginUser(PostgresAccountReader(), ScryptPasswordVerifier(),
                     JwtAccessTokenIssuer(), RedisLoginRateLimiter())


def update_profile_use_case() -> ProfileUseCases:
    return ProfileUseCases(PostgresProfileWriter(), embeddings, cache)
