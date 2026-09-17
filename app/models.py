"""Merkezi profil verisinin veri modelleri.

Tüm iş deneyimi, eğitim ve yetenek bilgisi burada tanımlanan modellere
uygun tek bir JSON dosyasında tutulur; CV üretimi ve (ileride) ilan
eşleştirmesi bu profil üzerinden çalışır.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class ContactInfo(BaseModel):
    full_name: str
    title: str
    email: EmailStr
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None


class Experience(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str | None = None  # None => "Halen"
    location: str | None = None
    highlights: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)


class Education(BaseModel):
    school: str
    degree: str
    field: str | None = None
    start_date: str
    end_date: str | None = None


class SkillGroup(BaseModel):
    category: str
    items: list[str]


class Profile(BaseModel):
    contact: ContactInfo
    summary: str | None = None
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[SkillGroup] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
