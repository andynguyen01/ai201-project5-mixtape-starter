from datetime import datetime, timedelta, timezone

import pytest

from app import create_app, db
from models import User, Song, ListeningEvent, friendships
from services.feed_service import get_friends_listening_now


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def add_friendship(user_a, user_b):
    db.session.execute(
        friendships.insert().values(user_id=user_a.id, friend_id=user_b.id)
    )
    db.session.execute(
        friendships.insert().values(user_id=user_b.id, friend_id=user_a.id)
    )


def test_listening_now_excludes_events_older_than_30_minutes(app):
    with app.app_context():
        now = datetime.now(timezone.utc)

        darius = User(username="darius", email="darius@test.com")
        simone = User(username="simone", email="simone@test.com")
        nova = User(username="nova", email="nova@test.com")

        db.session.add_all([darius, simone, nova])
        db.session.flush()

        add_friendship(darius, simone)
        add_friendship(darius, nova)

        song = Song(
            title="Test Song",
            artist="Test Artist",
            genre="lo-fi",
            shared_by=darius.id,
        )

        db.session.add(song)
        db.session.flush()

        recent_event = ListeningEvent(
            user_id=simone.id,
            song_id=song.id,
            listened_at=now - timedelta(minutes=18),
        )

        stale_event = ListeningEvent(
            user_id=nova.id,
            song_id=song.id,
            listened_at=now - timedelta(minutes=123),
        )

        db.session.add_all([recent_event, stale_event])
        db.session.commit()

        results = get_friends_listening_now(darius.id)
        result_text = str(results).lower()

        assert "simone" in result_text
        assert "nova" not in result_text