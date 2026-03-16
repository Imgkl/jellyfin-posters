from pydantic import BaseModel


class LoginRequest(BaseModel):
    server_url: str = ""
    username: str = ""
    password: str = ""


class ApplyImageRequest(BaseModel):
    type: str  # Primary, Backdrop, Logo
    url: str


class MarkReviewedRequest(BaseModel):
    poster_changed: bool = False
    backdrop_changed: bool = False
    logo_changed: bool = False
    poster_url: str = ""
    backdrop_url: str = ""
    logo_url: str = ""


class ImportRequest(BaseModel):
    mode: str = "merge"  # "merge" or "replace"
    records: list[dict]
