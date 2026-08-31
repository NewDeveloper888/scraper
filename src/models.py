import re
from pydantic import BaseModel, HttpUrl, field_validator


class RawBookRecord(BaseModel):
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: str
    fetched_at: str


class NormalizedBookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: HttpUrl
    fetched_at: str

    @classmethod
    def from_raw(cls, raw: RawBookRecord) -> "NormalizedBookRecord":
        """Clean raw values and return a validated normalized record."""
        # Extract numeric float from strings like "£51.77" or "Â£51.77"
        match = re.search(r"(\d+\.\d+|\d+)", raw.price_text)
        if not match:
            raise ValueError(
                f"Could not extract numeric price from '{raw.price_text}'"
            )

        price_gbp = float(match.group(1))

        return cls(
            title=raw.title,
            product_url=raw.product_url,  # type: ignore
            price_text=raw.price_text,
            price_gbp=price_gbp,
            availability_text=raw.availability_text,
            rating_text=raw.rating_text,
            description=raw.description,
            source_page=raw.source_page,  # type: ignore
            fetched_at=raw.fetched_at,
        )