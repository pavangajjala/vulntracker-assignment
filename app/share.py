"""Shared Report Link feature.

POST /scans/{scan_id}/share  (logged in)  -> creates a link valid for 24 hours
GET  /share/{token}          (public)     -> returns the scan if the link is valid

Security decisions (explained in docs/findings.md):
- Token: 32 random bytes from `secrets` (256 bits), impossible to guess.
- Only the SHA-256 hash of the token is stored in the database.
- Only the owner of a scan can share it.
- Optional password is stored as a bcrypt hash, never in plain text.
- After 5 wrong passwords the link is locked (stops brute force).
- Invalid, expired, locked and unknown links all get the same 404 answer.
- The public view returns only the fields an outsider needs (no owner_id).
- The password can be sent as a header (X-Share-Password) so it stays out of
  URLs and logs; the `password` query parameter is still accepted because
  the brief requires it.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

import models
from auth import get_current_user, get_password_hash, verify_password
from config import SHARE_BASE_URL
from database import get_db

router = APIRouter(tags=["share"])

SHARE_TTL = timedelta(hours=24)
MAX_PASSWORD_ATTEMPTS = 5


class ShareCreate(BaseModel):
    # bcrypt only uses the first 72 bytes, so longer passwords are rejected.
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)


class ShareCreated(BaseModel):
    share_url: str
    expires_at: datetime


class SharedScan(BaseModel):
    """What an external viewer is allowed to see."""
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: Optional[str]
    severity: str
    status: str
    cve_id: Optional[str]
    affected_component: str
    remediation_notes: Optional[str]
    created_at: datetime


def _utcnow() -> datetime:
    # SQLite stores datetimes without a timezone, so we keep UTC "naive" values.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/scans/{scan_id}/share", response_model=ShareCreated, status_code=status.HTTP_201_CREATED)
def create_share_link(
    scan_id: int,
    payload: Optional[ShareCreate] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    scan = db.query(models.ScanResult).filter(
        models.ScanResult.id == scan_id,
        models.ScanResult.owner_id == current_user.id,   # you can only share your own scans
    ).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    token = secrets.token_urlsafe(32)
    password = payload.password if payload else None
    link = models.ShareLink(
        token_hash=_hash_token(token),
        scan_id=scan.id,
        created_by=current_user.id,
        password_hash=get_password_hash(password) if password else None,
        expires_at=_utcnow() + SHARE_TTL,
    )
    db.add(link)
    db.commit()
    return ShareCreated(share_url=f"{SHARE_BASE_URL}/share/{token}", expires_at=link.expires_at)


@router.get("/share/{token}", response_model=SharedScan)
def view_shared_scan(
    token: str,
    password: Optional[str] = None,
    x_share_password: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    not_found = HTTPException(status_code=404, detail="Link not found or expired")
    if len(token) > 100:
        raise not_found

    link = db.query(models.ShareLink).filter(models.ShareLink.token_hash == _hash_token(token)).first()
    if not link or link.expires_at <= _utcnow() or link.failed_attempts >= MAX_PASSWORD_ATTEMPTS:
        raise not_found

    if link.password_hash:
        supplied = x_share_password or password
        if not supplied or not verify_password(supplied, link.password_hash):
            if supplied:
                link.failed_attempts += 1
                db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Password required or incorrect")

    scan = db.query(models.ScanResult).filter(models.ScanResult.id == link.scan_id).first()
    if not scan:
        raise not_found
    return scan