from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VendorCreate(BaseModel):
    """Data accepted when creating a vendor."""

    name: str = Field(
        min_length=1,
        max_length=100,
    )


class VendorRead(BaseModel):
    """Vendor data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime