from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List

class RoyaltySplitSchema(BaseModel):
    """Defines who gets what percentage of the streaming money"""
    collaborator_email: EmailStr
    share_percentage: float = Field(..., gt=0, le=100)

class TrackDistroSubmission(BaseModel):
    track_id: str
    title: str = Field(..., min_length=1, max_length=255)
    primary_artist: str = Field(..., min_length=1, max_length=255)
    genre: str
    audio_url: str      
    cover_art_url: str  
    splits: List[RoyaltySplitSchema]
    allow_sync_licensing: bool = Field(default=True, description="Allows the AI to package this track for movies/TV/commercials")
    license_type: str = Field(default="exclusive", description="e.g., exclusive, non-exclusive master clearance")

    @field_validator('splits')
    @classmethod
    def validate_total_splits(cls, v: List[RoyaltySplitSchema]) -> List[RoyaltySplitSchema]:
        total = sum(item.share_percentage for item in v)
        if not (99.9 <= total <= 100.1):
            raise ValueError(f"Total splits must equal exactly 100%. Got {total}%")
        return v