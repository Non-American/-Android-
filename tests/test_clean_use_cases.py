"""Unit tests: application behavior with fake ports, no DB or Redis required."""
import pytest
from app.application.use_cases.login import LoginUser
from app.application.use_cases.profile import ProfileUseCases
from app.domain.services.auth import InvalidCredentials, BannedAccount
from app.domain.services.profile import InvalidTags

class Accounts:
    def __init__(self, user): self.user = user
    def find_for_login(self, email):
        assert email == 'test@example.org'
        return self.user

class Passwords:
    def verify(self, plain, stored): return (plain, stored) == ('correct-password', 'hash')

class Tokens:
    def issue(self, uid): return f'token-{uid}'

class Limiter:
    def __init__(self): self.checked = []
    def check(self, email): self.checked.append(email)

def test_login_normalizes_email_and_creates_token():
    limiter = Limiter()
    case = LoginUser(Accounts({'id': 7, 'pw_hash': 'hash', 'banned_at': None}),
                     Passwords(), Tokens(), limiter)
    assert case.execute('TEST@EXAMPLE.ORG', 'correct-password') == {'token': 'token-7'}
    assert limiter.checked == ['test@example.org']

@pytest.mark.parametrize('user,password,error', [
    (None, 'correct-password', InvalidCredentials),
    ({'id': 7, 'pw_hash': 'hash', 'banned_at': None}, 'wrong-password', InvalidCredentials),
    ({'id': 7, 'pw_hash': 'hash', 'banned_at': 'today'}, 'correct-password', BannedAccount),
])
def test_login_rejects_invalid_accounts(user,password,error):
    case = LoginUser(Accounts(user), Passwords(), Tokens(), Limiter())
    with pytest.raises(error): case.execute('TEST@EXAMPLE.ORG', password)

class ProfileRepo:
    def __init__(self): self.saved = []
    def save_profile(self, *args): self.saved.append(args)

class Embeddings:
    def embed(self, tags): return [float(len(tags))]

class Cache:
    def __init__(self): self.invalidated = []
    def feed_drop(self, uid): self.invalidated.append(uid)

def test_profile_normalizes_saves_and_invalidates_cache():
    repo, cache = ProfileRepo(), Cache()
    case = ProfileUseCases(repo, Embeddings(), cache)
    tags = ['Jazz', 'Music', 'Travel', 'Cooking', 'Art']
    assert case.update(3, tags, ' hi ') == {'tags': sorted(t.lower() for t in tags)}
    assert repo.saved == [(3, sorted(t.lower() for t in tags), 'hi', [5.0])]
    assert cache.invalidated == [3]

def test_profile_invalid_tags_never_write():
    repo, cache = ProfileRepo(), Cache()
    with pytest.raises(InvalidTags):
        ProfileUseCases(repo, Embeddings(), cache).update(3, ['only'], 'hello')
    assert not repo.saved and not cache.invalidated
