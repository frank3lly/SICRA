"""Operational alert evaluation and lifecycle management service for SICRA."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.entities import Alert, Business, Container
from src.models.enums import AlertType

logger = logging.getLogger("sicra.services.alerts")


class AlertService:
    """Domain service managing capacity and maintenance alert evaluation."""

    @staticmethod
    def evaluate_container_alert(
        container: Container,
        db: Session,
        hours_to_80_percent: Optional[float] = None,
    ) -> Optional[Alert]:
        """Evaluate physical and predictive conditions to trigger or update active alerts (Requirement R-05).

        Conditions:
        - Physical Trigger: current_fill_percentage >= 80.0%
        - Predictive Trigger: hours_to_80_percent <= 24.0 hours

        Deduplication:
        - If an active alert of this type already exists, update triggered_percentage.
        """
        fill_pct = container.current_fill_percentage
        is_physical_alert = fill_pct >= 80.0
        is_predictive_alert = (
            hours_to_80_percent is not None
            and 0.0 <= hours_to_80_percent <= 24.0
        )

        if not (is_physical_alert or is_predictive_alert):
            return None

        # Determine target severity classification
        alert_type = (
            AlertType.CAPACITY_95_CRITICAL
            if fill_pct >= 95.0
            else AlertType.CAPACITY_80_PERCENT
        )

        # Check for existing unresolved alert to prevent duplicate records
        existing_alert = (
            db.query(Alert)
            .filter(
                Alert.container_id == container.id,
                Alert.alert_type == alert_type,
                Alert.is_resolved == False,
            )
            .first()
        )

        if existing_alert:
            existing_alert.triggered_percentage = round(fill_pct, 2)
            existing_alert.updated_at = datetime.now(timezone.utc)
            db.commit()
            return existing_alert

        # Create new active operational alert
        new_alert = Alert(
            container_id=container.id,
            alert_type=alert_type,
            triggered_percentage=round(fill_pct, 2),
            is_resolved=False,
        )
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)

        logger.info(
            f"Created {alert_type.value} alert for container {container.id} "
            f"(fill: {fill_pct:.1f}%, projected hours: {hours_to_80_percent})"
        )
        return new_alert

    @staticmethod
    def get_active_alerts(db: Session) -> List[Dict[str, Any]]:
        """Retrieve all unresolved alerts enriched with container and business metadata."""
        query = (
            db.query(Alert, Container, Business)
            .join(Container, Alert.container_id == Container.id)
            .join(Business, Container.business_id == Business.id)
            .filter(Alert.is_resolved == False)
            .order_by(Alert.triggered_percentage.desc(), Alert.created_at.asc())
        )

        results = []
        for alert, container, business in query.all():
            results.append(
                {
                    "alert_id": str(alert.id),
                    "container_id": str(container.id),
                    "business_id": str(business.id),
                    "business_name": business.name,
                    "address": business.address,
                    "city": business.city,
                    "latitude": business.latitude,
                    "longitude": business.longitude,
                    "alert_type": (
                        alert.alert_type.value
                        if hasattr(alert.alert_type, "value")
                        else str(alert.alert_type)
                    ),
                    "triggered_percentage": alert.triggered_percentage,
                    "current_volume_liters": container.current_volume_liters,
                    "capacity_liters": container.capacity_liters,
                    "is_resolved": alert.is_resolved,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                }
            )
        return results

    @staticmethod
    def resolve_alert(alert_id: str, db: Session) -> Alert:
        """Manually mark an active operational alert as resolved."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert '{alert_id}' not found",
            )

        if not alert.is_resolved:
            alert.is_resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            alert.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(alert)
            logger.info(f"Alert {alert_id} resolved successfully.")

        return alert
