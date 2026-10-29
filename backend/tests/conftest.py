import pytest


@pytest.fixture(autouse=True)
def isolate_database():
    """Keep API tests independent when the full suite runs in one process."""
    from database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
