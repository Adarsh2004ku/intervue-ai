from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import backend.routes.auth as auth
import backend.routes.health as health
import backend.routes.resume as resume
import backend.routes.interview as interview
import backend.routes.user as user
import backend.routes.testing as testing
import backend.routes.admin as admin

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/auth")
app.include_router(health.router, prefix="/health")
app.include_router(resume.router, prefix="/resume")
app.include_router(interview.router, prefix="/interview")
app.include_router(user.router, prefix="/user")
app.include_router(testing.router, prefix="/testing")
app.include_router(admin.router, prefix="/admin")