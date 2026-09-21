from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field, StringConstraints

LowerEmail = Annotated[EmailStr, AfterValidator(lambda value: value.lower())]
Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=50),
]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Percent = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]