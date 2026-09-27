"""Create the four local users and load the fake corpus."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from kp.auth import hash_password, utcnow
from kp.config import get_settings
from kp.corpus.generate import generate_corpus
from kp.corpus.load import load_corpus, write_corpus_files
from kp.db import SessionLocal, ensure_schema
from kp.labels import ROLES
from kp.models import User

# Extra skill ids live on the user. The CEO has one personal workflow; the others start empty.
SEEDED_SKILL_IDS = {
    "ceo": ["weekly-complaint-readout"],
    "operations_manager": [],
    "engineer": [],
    "marketing": [],
}


def seed_users(db: Session) -> None:
    settings = get_settings()
    now = utcnow()
    for persona in ROLES:
        existing = db.query(User).filter(User.username == persona).one_or_none()
        skill_ids = list(SEEDED_SKILL_IDS[persona])
        if existing:
            if not existing.skill_ids and skill_ids:
                existing.skill_ids = skill_ids
            continue
        db.add(
            User(
                id=str(uuid.uuid4()),
                username=persona,
                password_hash=hash_password(settings.seed_passwords[persona]),
                persona=persona,
                skill_ids=skill_ids,
                created_at=now,
            )
        )
    db.flush()


def seed_all(db: Session) -> None:
    settings = get_settings()
    seed_users(db)
    corpus = generate_corpus()
    write_corpus_files(corpus, settings.corpus_dir)
    load_corpus(db, corpus)


def main() -> None:
    ensure_schema()
    db = SessionLocal()
    try:
        seed_all(db)
        db.commit()
    finally:
        db.close()
    print("Seeded users and the support corpus.")


if __name__ == "__main__":
    main()
