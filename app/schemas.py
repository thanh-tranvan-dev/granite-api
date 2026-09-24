from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=9, max_length=16, pattern=r"^[+0-9() .-]+$")]
ShortText = Annotated[str | None, Field(max_length=300)]
LongText = Annotated[str | None, Field(max_length=3000)]


class LeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name
    phone: Phone
    service_slug: Annotated[str | None, Field(max_length=80)] = None
    message: LongText = None
    area: ShortText = None
    stone_type: ShortText = None
    expected_size: ShortText = None


class LeadCreated(BaseModel):
    id: str
    received_at: datetime
    message: str = "Yêu cầu đã được tiếp nhận."
