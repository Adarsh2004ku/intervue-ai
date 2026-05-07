from fastapi import APIRouter, HTTPException

router = APIRouter()


TEST_USERS = {
    "adarsh": {
        "token": "token_adarsh",
        "id": "user_1",
        "email": "adarsh@test.com",
    },
    "demo": {
        "token": "token_demo",
        "id": "user_2",
        "email": "demo@test.com",
    },
}


@router.get("/users")
async def users():
    return TEST_USERS


@router.post("/login/{username}")
async def login(username: str):
    user = TEST_USERS.get(username)
    if not user:
        raise HTTPException(404, "User not found")

    return {
        "access_token": user["token"],
        "user": user,
    }
