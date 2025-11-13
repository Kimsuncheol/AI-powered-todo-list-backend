from pydantic import BaseModel, EmailStr, Field


class SignUpIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None


class SignInIn(BaseModel):
    email: EmailStr
    password: str
    rememberMe: bool | None = False


class OtpStartIn(BaseModel):
    email: EmailStr


class OtpVerifyIn(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class PasswordResetIn(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str | None = None
    tz: str
    locale: str
    emailVerified: bool


class AuthEnvelope(BaseModel):
    data: UserPublic
