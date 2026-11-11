"""Application use cases. The adapter is supplied by the composition root."""

class ChatUseCases:
    def __init__(self, gateway):
        self.gateway = gateway

    def matches(self, u):
        return self.gateway.matches(u)

    def history(self, other, before, limit, u):
        return self.gateway.history(other, before, limit, u)

    def send(self, other, m, u):
        return self.gateway.send(other, m, u)

    def mark_read(self, other, u):
        return self.gateway.mark_read(other, u)

    async def ws(self, websocket):
        return await self.gateway.ws(websocket)

