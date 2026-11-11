"""Application use cases. The adapter is supplied by the composition root."""

class AuthUseCases:
    def __init__(self, gateway):
        self.gateway = gateway

    def register(self, r, bg):
        return self.gateway.register(r, bg)

    def verify_email(self, token):
        return self.gateway.verify_email(token)

    def resend(self, bg, u):
        return self.gateway.resend(bg, u)

    def me(self, u):
        return self.gateway.me(u)

