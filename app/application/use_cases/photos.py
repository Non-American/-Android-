"""Application use cases. The adapter is supplied by the composition root."""

class PhotosUseCases:
    def __init__(self, gateway):
        self.gateway = gateway

    async def upload(self, file, u):
        return await self.gateway.upload(file, u)

    def delete(self, pid, u):
        return self.gateway.delete(pid, u)

    def make_main(self, pid, u):
        return self.gateway.make_main(pid, u)

