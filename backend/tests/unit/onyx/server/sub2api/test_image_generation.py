from onyx.server.sub2api.image_generation import build_sub2api_image_credentials


class FakeEncryptedValue:
    def __init__(self, value: str) -> None:
        self.value = value

    def get_value(self, apply_mask: bool = False) -> str:
        return "****" if apply_mask else self.value


class FakeCredential:
    def __init__(self, api_key: str) -> None:
        self.api_key = FakeEncryptedValue(api_key)


def test_build_sub2api_image_credentials_uses_user_key_and_configured_api_base(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "onyx.server.sub2api.image_generation.resolve_sub2api_api_base_url",
        lambda: "http://127.0.0.1:8080/v1",
    )

    credentials = build_sub2api_image_credentials(FakeCredential("sk-user"))

    assert credentials.api_key == "sk-user"
    assert credentials.api_base == "http://127.0.0.1:8080/v1"
