from pydantic import BaseModel


class InputImgSchema(BaseModel):
    img_base64str: str
