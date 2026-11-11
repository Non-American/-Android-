"""Application use cases. The adapter is supplied by the composition root."""

class ModerationUseCases:
    def __init__(self, gateway):
        self.gateway = gateway

    def block(self, other, u):
        return self.gateway.block(other, u)

    def report(self, other, r, u):
        return self.gateway.report(other, r, u)

    def reports(self, status, limit, _):
        return self.gateway.reports(status, limit, _)

    def resolve(self, rid, body, a):
        return self.gateway.resolve(rid, body, a)

    def unban(self, uid, _):
        return self.gateway.unban(uid, _)

    def delete_photo(self, pid, _):
        return self.gateway.delete_photo(pid, _)

