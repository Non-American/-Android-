"""Application use cases. The adapter is supplied by the composition root."""

class FeedUseCases:
    def __init__(self, gateway):
        self.gateway = gateway

    def feed(self, limit, u):
        return self.gateway.feed(limit, u)

    def swipe(self, s, u):
        return self.gateway.swipe(s, u)

