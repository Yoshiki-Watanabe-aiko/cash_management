from pydantic import BaseModel, ConfigDict, Field


class CategoryRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    keyword_pattern: str
    category_id: int
    priority: int


class CategoryRuleCreate(BaseModel):
    keyword_pattern: str = Field(min_length=1, max_length=255)
    category_id: int
    priority: int = 100


class CategoryRuleUpdate(BaseModel):
    keyword_pattern: str | None = Field(default=None, min_length=1, max_length=255)
    category_id: int | None = None
    priority: int | None = None
