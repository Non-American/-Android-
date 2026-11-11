"""HTTP input contracts belong to Presentation."""
from pydantic import BaseModel, Field

class Prof(BaseModel):
    tags: list[str] = Field(min_length=5, max_length=10)
    bio: str = Field('', max_length=500)
