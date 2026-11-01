"""Request, story, and judge response validation."""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Story(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    story: str = Field(min_length=40, max_length=14000)

class StoryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    prompt: str = Field(min_length=3, max_length=1200)
    age: int = Field(default=7, ge=5, le=10, strict=True)
    length: str = Field(default='short', pattern='^(short|long)$')

    feedback: str | None = Field(default=None, min_length=3, max_length=1200)
    previous_story: Story | None = None

    @field_validator('feedback')
    @classmethod
    def clean_feedback(cls, value):
        if value is not None:
            value = value.strip()
            if len(value) < 3:
                raise ValueError('Enter at least three non-space characters of feedback.')
        return value

    @model_validator(mode='after')
    def feedback_requires_story(self):
        if (self.feedback is None) != (self.previous_story is None):
            raise ValueError('Feedback and previous_story must be provided together.')
        return self

    @field_validator('prompt')
    @classmethod
    def clean_prompt(cls, value):
        value = value.strip()
        if len(value) < 3:
            raise ValueError('Enter at least three non-space characters.')
        return value

class Scores(BaseModel):
    age_fit: int = Field(ge=1, le=5, strict=True)
    story_arc: int = Field(ge=1, le=5, strict=True)
    warmth: int = Field(ge=1, le=5, strict=True)
    bedtime: int = Field(ge=1, le=5, strict=True)
    request_fit: int = Field(ge=1, le=5, strict=True)

class Review(BaseModel):
    safe: bool = Field(strict=True)
    scores: Scores
    feedback: str = Field(min_length=1, max_length=3000)

