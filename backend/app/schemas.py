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

class LocationCreate(BaseModel):
    """Data accepted when creating a restaurant location."""

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    square_location_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )

    timezone: str = Field(
        default="America/New_York",
        min_length=1,
        max_length=64,
    )

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
    )


class LocationRead(BaseModel):
    """Location data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    square_location_id: str | None
    timezone: str
    currency: str
    is_active: bool
    created_at: datetime