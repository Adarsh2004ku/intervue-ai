from fastapi import Header, HTTPException


FAKE_USERS = {
    "token_adarsh": {
        "id": "user_1",
        "email": "adarsh@test.com"
    },

    "token_demo": {
        "id": "user_2",
        "email": "demo@test.com"
    }
}


async def get_current_user(
    authorization: str = Header(None)
):

    # fallback default token
    if not authorization:
        authorization = "Bearer token_adarsh"

    token = authorization.replace("Bearer ", "")

    user = FAKE_USERS.get(token)

    if not user:
        raise HTTPException(401, "Invalid token")

    return user


def verify_token(token: str):

    user = FAKE_USERS.get(token)

    if not user:
        raise HTTPException(401, "Invalid token")

    return user