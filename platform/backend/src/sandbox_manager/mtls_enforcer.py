"""Stub MTLSEnforcer."""


class MTLSEnforcer:
    def __init__(self, *args, **kwargs):
        pass

    def validate_client_certificate(self, cert_data: bytes) -> dict:
        return {"valid": False}

    def generate_certificate(self, *args, **kwargs):
        return {}
