import os
from typing import List

import pytest
from datetime import datetime

from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.fake import make_fake_forecasts
from nowcasting_datamodel.models.forecast import ForecastSQL
from nowcasting_datamodel.models import MLModelSQL
from nowcasting_datamodel.save.save import save
from testcontainers.postgres import PostgresContainer


@pytest.fixture
def forecasts(db_session):
    t0_datetime_utc = datetime.utcnow()
    # create
    for model_name in ["cnn", "pvnet_v2", "National_xg"]:

        if model_name == "National_xg":
            gsp_ids = [0]
        else:
            gsp_ids = list(range(0, 11))

        f = make_fake_forecasts(
            gsp_ids=gsp_ids,
            session=db_session,
            model_name=model_name,
            n_fake_forecasts=16,
            t0_datetime_utc=t0_datetime_utc,  # add
        )  # add

        save(forecasts=f, session=db_session, apply_adjuster=False)

    return None


"""
This is a bit complicated and sensitive to change
https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2 helped me get going
"""


@pytest.fixture(scope="session")
def engine_url():
    """Database engine, this includes the table creation."""
    with PostgresContainer("postgres:14.5") as postgres:
        url = postgres.get_connection_url()
        os.environ["DB_URL"] = url

        database_connection = DatabaseConnection(url, echo=False)

        engine = database_connection.engine

        # Would like to do this here but found the data
        # was not being deleted when using 'db_connection'
        # database_connection.create_all()
        # Base_PV.metadata.create_all(engine)

        yield url

        # Base_PV.metadata.drop_all(engine)
        # Base_Forecast.metadata.drop_all(engine)

        engine.dispose()


@pytest.fixture()
def db_connection(engine_url):
    database_connection = DatabaseConnection(engine_url, echo=False)

    engine = database_connection.engine
    # connection = engine.connect()
    # transaction = connection.begin()

    # There should be a way to only make the tables once
    # but make sure we remove the data
    database_connection.create_all()

    yield database_connection

    # transaction.rollback()
    # connection.close()

    database_connection.drop_all()


@pytest.fixture(scope="function", autouse=True)
def db_session(db_connection, engine_url):
    """Creates a new database session for a test."""

    # connection = db_connection.engine.connect()
    # t = connection.begin()

    with db_connection.Session() as s:
        s.begin()
        yield s
        s.rollback()

    # t.rollback()
    # connection.close()