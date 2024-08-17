from pydantic import BaseModel


class LoginSchema(BaseModel):
    ip: str
    temp: int
    gathering_map: str
