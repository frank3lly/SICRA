"""Predictive modeling and daily generation forecast REST API endpoints for SICRA."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.ml.inference import InferenceEngine
from src.models.entities import Business, Container, Prediction, User
from src.models.enums import ContainerStatus, UserRole
from src.security.dependencies import (
    get_current_user,
    require_role,
    verify_business_access,
)

router = APIRouter()

# Singleton-style lazy loader for production inference engine
_engine_instance = None


def get_inference_engine() -> InferenceEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = InferenceEngine()
    return _engine_instance


@router.get(
    "/latest",
    summary="Get latest volumetric predictions for active fleet containers",
)
def get_fleet_predictions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Retrieve latest prediction records for all active containers."""
    containers = (
        db.query(Container, Business)
        .join(Business, Container.business_id == Business.id)
        .filter(Container.status == ContainerStatus.ACTIVE)
        .all()
    )

    results = []
    for container, business in containers:
        latest_pred = (
            db.query(Prediction)
            .filter(Prediction.container_id == container.id)
            .order_by(Prediction.calculation_timestamp.desc())
            .first()
        )
        if latest_pred:
            daily_liters = round(float(latest_pred.predicted_daily_liters or 0.0), 1)
            cap = float(container.capacity_liters or 50.0)
            current_pct = round(float(container.current_fill_percentage or 0.0), 1)
            current_vol = float(container.current_volume_liters or 0.0)
            forecast_liters = current_vol + daily_liters
            forecast_pct = round(min(100.0, (forecast_liters / cap) * 100.0), 1)

            results.append({
                "container_id": str(container.id),
                "name": business.name,
                "dailyLiters": daily_liters,
                "currentPct": current_pct,
                "forecastPct": forecast_pct,
                "calculation_timestamp": latest_pred.calculation_timestamp.isoformat(),
            })

    return results


@router.get(
    "/container/{id}",
    summary="Get latest volumetric forecast and hours until 80% capacity",
)
def get_container_prediction(
    id: str = Path(..., description="UUID of the smart container"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve the latest predictive forecast or execute on-demand projection."""
    container = db.query(Container).filter(Container.id == id).first()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Container '{id}' not found",
        )

    verify_business_access(container.business_id, current_user)

    # 1. Check existing recent prediction
    today = date.today()
    existing_pred = (
        db.query(Prediction)
        .filter(
            Prediction.container_id == container.id,
            Prediction.target_date == today,
        )
        .order_by(Prediction.calculation_timestamp.desc())
        .first()
    )

    if existing_pred:
        return {
            "container_id": str(container.id),
            "calculation_timestamp": existing_pred.calculation_timestamp.isoformat(),
            "target_date": existing_pred.target_date.isoformat(),
            "predicted_daily_liters": existing_pred.predicted_daily_liters,
            "projected_hours_to_80_percent": existing_pred.projected_hours_to_80_percent,
            "model_identifier": existing_pred.model_identifier,
        }

    # 2. On-demand inference
    business = db.query(Business).filter(Business.id == container.business_id).first()
    engine = get_inference_engine()

    b_type = (
        business.business_type.value
        if hasattr(business.business_type, "value")
        else str(business.business_type)
    ) if business else "FRITURA"
    fryers = business.num_fryers if business else 2
    customers = business.avg_daily_customers if business else 100
    day_of_week = today.weekday()

    pred_liters = engine.predict_daily_volume(
        business_type=b_type,
        num_fryers=fryers,
        avg_daily_customers=customers,
        day_of_week=day_of_week,
        lag_7d_liters=container.current_volume_liters,
        business_id=str(business.id) if business else None,
    )

    hours_to_80 = engine.predict_hours_to_80_percent(
        current_liters=container.current_volume_liters,
        capacity_liters=container.capacity_liters,
        daily_pour_rate=pred_liters,
    )

    model_name = getattr(engine.model, "__class__", type(engine.model)).__name__
    now_utc = datetime.now(timezone.utc)

    # Persist prediction
    new_pred = Prediction(
        container_id=container.id,
        calculation_timestamp=now_utc,
        target_date=today,
        predicted_daily_liters=round(pred_liters, 2),
        projected_hours_to_80_percent=round(hours_to_80, 1) if hours_to_80 != float("inf") else None,
        model_identifier=model_name,
        is_synthetic=False,
    )
    db.add(new_pred)
    db.commit()

    return {
        "container_id": str(container.id),
        "calculation_timestamp": now_utc.isoformat(),
        "target_date": today.isoformat(),
        "predicted_daily_liters": round(pred_liters, 2),
        "projected_hours_to_80_percent": round(hours_to_80, 1) if hours_to_80 != float("inf") else None,
        "model_identifier": model_name,
    }


@router.post(
    "/run-forecast",
    summary="Batch execute ML predictions across fleet (Admin only)",
)
def run_fleet_forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> Dict[str, Any]:
    """Execute predictive forecasting for all active smart containers in the network."""
    containers = (
        db.query(Container, Business)
        .join(Business, Container.business_id == Business.id)
        .filter(Container.status == ContainerStatus.ACTIVE)
        .all()
    )

    engine = get_inference_engine()
    today = date.today()
    now_utc = datetime.now(timezone.utc)
    model_name = getattr(engine.model, "__class__", type(engine.model)).__name__

    generated_count = 0
    for container, business in containers:
        pred_liters = engine.predict_daily_volume(
            business_type=(
                business.business_type.value
                if hasattr(business.business_type, "value")
                else str(business.business_type)
            ),
            num_fryers=business.num_fryers,
            avg_daily_customers=business.avg_daily_customers,
            day_of_week=today.weekday(),
            lag_7d_liters=container.current_volume_liters,
            business_id=str(business.id),
        )

        hours_to_80 = engine.predict_hours_to_80_percent(
            current_liters=container.current_volume_liters,
            capacity_liters=container.capacity_liters,
            daily_pour_rate=pred_liters,
        )

        pred_record = Prediction(
            container_id=container.id,
            calculation_timestamp=now_utc,
            target_date=today,
            predicted_daily_liters=round(pred_liters, 2),
            projected_hours_to_80_percent=round(hours_to_80, 1) if hours_to_80 != float("inf") else None,
            model_identifier=model_name,
            is_synthetic=False,
        )
        db.add(pred_record)
        generated_count += 1

    db.commit()

    return {
        "status": "forecast_completed",
        "containers_processed": len(containers),
        "predictions_generated": generated_count,
    }
