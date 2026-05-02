from pydantic import BaseModel


class Sub2APIExchangeUser(BaseModel):
    id: int
    email: str
    username: str


class Sub2APICredentialPayload(BaseModel):
    api_key_id: int
    api_key: str
    api_base_url: str
    text_model_name: str
    image_model_name: str


class Sub2APILaunchExchangeResponse(BaseModel):
    user: Sub2APIExchangeUser
    credential: Sub2APICredentialPayload

    @classmethod
    def from_sub2api_payload(
        cls,
        payload: dict,
    ) -> "Sub2APILaunchExchangeResponse":
        return cls(
            user=Sub2APIExchangeUser(
                id=payload["user_id"],
                email=payload["email"],
                username=payload["username"],
            ),
            credential=Sub2APICredentialPayload(
                api_key_id=payload["api_key_id"],
                api_key=payload["api_key"],
                api_base_url=payload["api_base_url"],
                text_model_name=payload["text_model_name"],
                image_model_name=payload["image_model_name"],
            ),
        )
