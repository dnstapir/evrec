from jwcrypto.jwk import JWK, JWKSet

from dnstapir.key_resolver import KeyResolver


class EvrecJWKSet(JWKSet):
    def __init__(self, key_resolver: KeyResolver):
        super().__init__()
        self.key_resolver = key_resolver

    def get_key(self, kid: str) -> JWK:
        return JWK.from_pyca(self.key_resolver.resolve_public_key(kid))

    def get_keys(self, kid: str) -> list[JWK]:
        return [self.get_key(kid)]
