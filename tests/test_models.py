"""Unit tests for SICRA SQLAlchemy 2.0 ORM models and Pydantic schemas."""

from datetime import date, datetime, timezone
import pytest
from pydantic import ValidationError
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from src.database.session import get_engine, get_session_factory
from src.models import (
    Alert,
    Alerta,
    AlertType,
    Base,
    Business,
    BusinessCreate,
    BusinessResponse,
    BusinessType,
    CollectionRoute,
    Container,
    ContainerCreate,
    ContainerResponse,
    ContainerStatus,
    Negocio,
    Prediccion,
    Prediction,
    Recipiente,
    RouteStatus,
    RouteStop,
    RutaRecoleccion,
    Telemetry,
    TelemetryCreate,
    TelemetryFlag,
    TelemetryResponse,
    Telemetria,
    User,
    UserCreate,
    UserResponse,
    UserRole,
    Usuario,
)


@pytest.fixture
def db_engine():
    """In-memory SQLite database engine with foreign key enforcement."""
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """Database session fixture using in-memory engine."""
    session_factory = get_session_factory(db_engine)
    session: Session = session_factory()
    yield session
    session.rollback()
    session.close()


def test_table_generation(db_engine):
    """Assert all 7 core tables are created without schema conflicts."""
    inspector = inspect(db_engine)
    table_names = set(inspector.get_table_names())
    expected_tables = {
        "businesses",
        "containers",
        "telemetries",
        "predictions",
        "alerts",
        "collection_routes",
        "users",
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


def test_instantiate_and_persist_all_models(db_session: Session):
    """Assert all models can be persisted and retrieved with proper relationships."""
    now = datetime.now(timezone.utc)
    today = date.today()

    # 1. Business
    biz = Business(
        name="Pica Pollo Expreso SPM",
        business_type=BusinessType.PICA_POLLO,
        num_fryers=3,
        avg_daily_customers=250,
        latitude=18.4550,
        longitude=-69.3050,
        address="Av. Independencia 45, San Pedro de Macorís",
        city="San Pedro de Macorís",
        contact_name="Juan Perez",
        phone="809-555-0101",
        is_active=True,
    )
    db_session.add(biz)
    db_session.commit()
    assert biz.id is not None
    assert biz.created_at is not None

    # 2. Container
    container = Container(
        business_id=biz.id,
        device_token="token_hash_abc123xyz789",
        capacity_liters=50.0,
        tare_weight_kg=2.5,
        oil_density_kg_l=0.92,
        status=ContainerStatus.ACTIVE,
        current_volume_liters=10.5,
        current_fill_percentage=21.0,
        last_telemetry_at=now,
    )
    db_session.add(container)
    db_session.commit()
    assert container.id is not None

    # 3. User (Business Owner & Collector)
    owner = User(
        email="owner@picapollo.do",
        hashed_password="bcrypt_hash_secret",
        full_name="Juan Perez",
        role=UserRole.BUSINESS_OWNER,
        business_id=biz.id,
        is_active=True,
    )
    collector = User(
        email="driver@reoil.do",
        hashed_password="bcrypt_hash_secret2",
        full_name="Carlos Conductor",
        role=UserRole.COLLECTOR,
        business_id=None,
        is_active=True,
    )
    db_session.add_all([owner, collector])
    db_session.commit()

    # 4. Telemetry
    telemetry = Telemetry(
        container_id=container.id,
        measurement_timestamp=now,
        raw_weight_kg=12.16,
        calculated_liters=10.5,
        fill_percentage=21.0,
        battery_voltage_mv=4150,
        battery_percentage=98.0,
        is_synthetic=True,
        flag=TelemetryFlag.NORMAL,
    )
    db_session.add(telemetry)
    db_session.commit()
    assert isinstance(telemetry.id, int)

    # 5. Prediction
    prediction = Prediction(
        container_id=container.id,
        calculation_timestamp=now,
        target_date=today,
        predicted_daily_liters=6.2,
        projected_hours_to_80_percent=72.5,
        model_identifier="glm_gamma_v1",
        is_synthetic=True,
        historical_mae=0.45,
    )
    db_session.add(prediction)
    db_session.commit()
    assert prediction.id is not None

    # 6. Alert
    alert = Alert(
        container_id=container.id,
        alert_type=AlertType.CAPACITY_80_PERCENT,
        triggered_percentage=81.5,
        is_resolved=False,
    )
    db_session.add(alert)
    db_session.commit()
    assert alert.id is not None

    # 7. Collection Route
    route_stop = {
        "sequence": 1,
        "business_id": biz.id,
        "business_name": biz.name,
        "latitude": biz.latitude,
        "longitude": biz.longitude,
        "estimated_liters": 40.0,
    }
    route = CollectionRoute(
        scheduled_date=today,
        status=RouteStatus.SUGGESTED,
        total_distance_km=12.4,
        total_estimated_volume_liters=40.0,
        stops_order_json=[route_stop],
        collector_user_id=collector.id,
    )
    db_session.add(route)
    db_session.commit()
    assert route.id is not None

    # Assert relations
    queried_biz = db_session.get(Business, biz.id)
    assert len(queried_biz.containers) == 1
    assert queried_biz.containers[0].id == container.id
    assert len(queried_biz.containers[0].telemetries) == 1
    assert len(queried_biz.containers[0].predictions) == 1
    assert len(queried_biz.containers[0].alerts) == 1
    assert len(collector.collection_routes) == 1


def test_cascade_delete(db_session: Session):
    """Verify deleting a Business cascade-deletes Container and its child entities."""
    biz = Business(
        name="Fritura El Primo",
        business_type=BusinessType.FRITURA,
        num_fryers=2,
        avg_daily_customers=120,
        latitude=18.456,
        longitude=-69.304,
        address="Calle Duarte 12",
    )
    db_session.add(biz)
    db_session.commit()

    container = Container(
        business_id=biz.id,
        device_token="token_delete_cascade_test",
        capacity_liters=20.0,
    )
    db_session.add(container)
    db_session.commit()

    telemetry = Telemetry(
        container_id=container.id,
        measurement_timestamp=datetime.now(timezone.utc),
        raw_weight_kg=5.0,
        calculated_liters=2.5,
        fill_percentage=12.5,
    )
    alert = Alert(
        container_id=container.id,
        alert_type=AlertType.BATTERY_LOW,
        triggered_percentage=12.5,
    )
    prediction = Prediction(
        container_id=container.id,
        calculation_timestamp=datetime.now(timezone.utc),
        target_date=date.today(),
        predicted_daily_liters=3.0,
        model_identifier="test_model",
    )
    db_session.add_all([telemetry, alert, prediction])
    db_session.commit()

    t_id = telemetry.id
    a_id = alert.id
    p_id = prediction.id
    c_id = container.id

    # Delete business
    db_session.delete(biz)
    db_session.commit()

    # Verify everything cascaded
    assert db_session.get(Container, c_id) is None
    assert db_session.get(Telemetry, t_id) is None
    assert db_session.get(Alert, a_id) is None
    assert db_session.get(Prediction, p_id) is None


def test_foreign_key_violation_enforcement(db_session: Session):
    """Verify foreign key enforcement rejects orphaned records."""
    orphan_container = Container(
        business_id="non-existent-uuid-12345",
        device_token="token_orphan_test",
        capacity_liters=50.0,
    )
    db_session.add(orphan_container)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_enum_validation_error_on_invalid_string(db_session: Session):
    """Verify enum validation rejects invalid string values."""
    invalid_biz = Business(
        name="Invalid Biz Type Test",
        business_type="INVALID_FOOD_TRUCK",  # type: ignore
        latitude=18.45,
        longitude=-69.30,
        address="Test Address",
    )
    db_session.add(invalid_biz)
    with pytest.raises(StatementError):
        db_session.commit()


def test_is_synthetic_defaults_to_true(db_session: Session):
    """Verify is_synthetic defaults to True on Telemetry and Prediction records."""
    biz = Business(
        name="Cafeteria Central",
        business_type=BusinessType.CAFETERIA,
        latitude=18.45,
        longitude=-69.30,
        address="UCE Campus",
    )
    db_session.add(biz)
    db_session.commit()

    container = Container(
        business_id=biz.id,
        device_token="token_default_synthetic_test",
        capacity_liters=20.0,
    )
    db_session.add(container)
    db_session.commit()

    telemetry = Telemetry(
        container_id=container.id,
        measurement_timestamp=datetime.now(timezone.utc),
        raw_weight_kg=4.0,
        calculated_liters=1.5,
        fill_percentage=7.5,
    )
    prediction = Prediction(
        container_id=container.id,
        calculation_timestamp=datetime.now(timezone.utc),
        target_date=date.today(),
        predicted_daily_liters=2.5,
        model_identifier="baseline_seasonal",
    )
    db_session.add_all([telemetry, prediction])
    db_session.commit()

    db_session.refresh(telemetry)
    db_session.refresh(prediction)

    assert telemetry.is_synthetic is True
    assert prediction.is_synthetic is True


def test_spanish_aliases():
    """Verify Spanish entity aliases resolve to identical classes."""
    assert Negocio is Business
    assert Recipiente is Container
    assert Telemetria is Telemetry
    assert Prediccion is Prediction
    assert Alerta is Alert
    assert RutaRecoleccion is CollectionRoute
    assert Usuario is User


def test_pydantic_schema_validation():
    """Verify Pydantic V2 schemas perform validation and ORM serialization."""
    valid_biz_data = {
        "name": "Pica Pollo San Pedro",
        "business_type": "PICA_POLLO",
        "num_fryers": 2,
        "avg_daily_customers": 150,
        "latitude": 18.452,
        "longitude": -69.302,
        "address": "Calle Central 10",
        "city": "San Pedro de Macorís",
    }
    create_schema = BusinessCreate(**valid_biz_data)
    assert create_schema.business_type == BusinessType.PICA_POLLO

    # Invalid enum string in Pydantic
    with pytest.raises(ValidationError):
        BusinessCreate(**{**valid_biz_data, "business_type": "FAST_FOOD_UNKNOWN"})

    # Invalid customer count
    with pytest.raises(ValidationError):
        BusinessCreate(**{**valid_biz_data, "avg_daily_customers": -10})

    # RouteStop validation
    stop = RouteStop(
        sequence=1,
        business_id="biz-uuid-1",
        business_name="Fritura Dona Ana",
        latitude=18.45,
        longitude=-69.30,
        estimated_liters=25.0,
    )
    assert stop.sequence == 1
    assert stop.estimated_liters == 25.0


def test_unique_constraints(db_session: Session):
    """Verify unique constraints on device_token and user email."""
    biz = Business(
        name="Unique Test Biz",
        business_type=BusinessType.FRITURA,
        latitude=18.45,
        longitude=-69.30,
        address="Test",
    )
    db_session.add(biz)
    db_session.commit()

    # 1. Device Token Uniqueness
    c1 = Container(business_id=biz.id, device_token="DUPLICATE_TOKEN", capacity_liters=50.0)
    c2 = Container(business_id=biz.id, device_token="DUPLICATE_TOKEN", capacity_liters=20.0)
    db_session.add(c1)
    db_session.commit()

    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 2. User Email Uniqueness
    u1 = User(
        email="unique@sicra.do",
        hashed_password="hash",
        full_name="User One",
        role=UserRole.ADMIN,
    )
    u2 = User(
        email="unique@sicra.do",
        hashed_password="hash",
        full_name="User Two",
        role=UserRole.COLLECTOR,
    )
    db_session.add(u1)
    db_session.commit()

    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_orm_to_pydantic_roundtrip(db_session: Session):
    """Verify ORM models serialize properly into Pydantic V2 response schemas."""
    biz = Business(
        name="Cafeteria Modelo",
        business_type=BusinessType.CAFETERIA,
        num_fryers=1,
        avg_daily_customers=80,
        latitude=18.453,
        longitude=-69.301,
        address="Av. Independencia 10",
        city="San Pedro de Macorís",
    )
    db_session.add(biz)
    db_session.commit()

    pydantic_biz = BusinessResponse.model_validate(biz)
    assert pydantic_biz.id == biz.id
    assert pydantic_biz.name == "Cafeteria Modelo"
    assert pydantic_biz.business_type == BusinessType.CAFETERIA
    assert pydantic_biz.created_at == biz.created_at

