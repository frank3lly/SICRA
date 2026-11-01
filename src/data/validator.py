"""Data integrity, physical sanity, and Dominican statistical profile auditor."""

from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.session import SessionLocal
from src.models.entities import Business, Container, Telemetry
from src.models.enums import BusinessType


class DataIntegrityError(Exception):
    """Raised when data integrity or sanity validations fail."""

    pass


class DataIntegrityAuditor:
    """Automated data quality and physical law auditor for telemetry and features."""

    def __init__(self, db_session: Optional[Session] = None) -> None:
        """Initialize auditor with optional SQLAlchemy session."""
        self.db_session = db_session

    def validate_database_integrity(
        self,
        session: Optional[Session] = None,
        raise_on_error: bool = True,
    ) -> Dict[str, Any]:
        """Run complete integrity audit against the connected database."""
        sess = session or self.db_session or SessionLocal()
        should_close = sess != self.db_session and session is None

        results: Dict[str, Any] = {
            "status": "PASSED",
            "physical_checks": {},
            "relational_checks": {},
            "statistical_checks": {},
            "errors": [],
        }

        try:
            # 1. Physical plausibility checks
            total_telemetries = sess.query(func.count(Telemetry.id)).scalar() or 0
            if total_telemetries == 0:
                results["status"] = "SKIPPED_EMPTY"
                return results

            negative_liters = (
                sess.query(func.count(Telemetry.id))
                .filter(Telemetry.calculated_liters < 0.0)
                .scalar()
                or 0
            )
            overfilled_containers = (
                sess.query(func.count(Telemetry.id))
                .filter(Telemetry.fill_percentage > 105.0)
                .scalar()
                or 0
            )
            invalid_voltage = (
                sess.query(func.count(Telemetry.id))
                .filter(
                    Telemetry.battery_voltage_mv.isnot(None),
                    (Telemetry.battery_voltage_mv < 3200) | (Telemetry.battery_voltage_mv > 4350),
                )
                .scalar()
                or 0
            )

            results["physical_checks"] = {
                "negative_liters_count": negative_liters,
                "overfilled_count": overfilled_containers,
                "invalid_voltage_count": invalid_voltage,
                "passed": (negative_liters == 0 and overfilled_containers == 0 and invalid_voltage == 0),
            }

            if negative_liters > 0:
                results["errors"].append(f"Found {negative_liters} records with negative calculated liters.")
            if overfilled_containers > 0:
                results["errors"].append(f"Found {overfilled_containers} records exceeding 105% capacity.")
            if invalid_voltage > 0:
                results["errors"].append(f"Found {invalid_voltage} records with battery voltage outside 3200-4350 mV.")

            # 2. Relational and provenance checks
            orphaned_telemetry = (
                sess.query(func.count(Telemetry.id))
                .outerjoin(Container, Telemetry.container_id == Container.id)
                .filter(Container.id.is_(None))
                .scalar()
                or 0
            )
            non_synthetic_count = (
                sess.query(func.count(Telemetry.id))
                .filter(Telemetry.is_synthetic.is_(False))
                .scalar()
                or 0
            )

            results["relational_checks"] = {
                "orphaned_telemetries": orphaned_telemetry,
                "non_synthetic_records": non_synthetic_count,
                "passed": (orphaned_telemetry == 0 and non_synthetic_count == 0),
            }

            if orphaned_telemetry > 0:
                results["errors"].append(f"Found {orphaned_telemetry} orphaned telemetry records.")
            if non_synthetic_count > 0:
                results["errors"].append(f"Found {non_synthetic_count} records where is_synthetic is False.")

            # 3. Statistical profile checks (Dominican Gastro-Profile on generated volume)
            from src.data.aggregator import DailyFeatureAggregator

            aggregator = DailyFeatureAggregator(db_session=sess)
            daily_df = aggregator.aggregate_daily_features(session=sess)

            if not daily_df.empty:
                # Group by business type mean daily liters
                mean_by_type = daily_df.groupby("business_type")["daily_liters"].mean().to_dict()
                pica_mean = mean_by_type.get(BusinessType.PICA_POLLO.value, mean_by_type.get(BusinessType.PICA_POLLO, 0.0))
                fritura_mean = mean_by_type.get(BusinessType.FRITURA.value, mean_by_type.get(BusinessType.FRITURA, 0.0))
                cafe_mean = mean_by_type.get(BusinessType.CAFETERIA.value, mean_by_type.get(BusinessType.CAFETERIA, 0.0))

                type_hierarchy_passed = bool(pica_mean > fritura_mean > cafe_mean)

                # Group by weekday (Mon-Wed: 0,1,2) vs weekend (Fri-Sun: 4,5,6)
                weekday_mean = daily_df[daily_df["day_of_week"].isin([0, 1, 2])]["daily_liters"].mean()
                weekend_mean = daily_df[daily_df["day_of_week"].isin([4, 5, 6])]["daily_liters"].mean()

                ratio = (weekend_mean / max(0.001, weekday_mean)) if weekday_mean > 0 else 1.0
                weekend_lift_passed = bool(ratio >= 1.4)

                results["statistical_checks"] = {
                    "mean_pica_pollo": round(float(pica_mean), 3),
                    "mean_fritura": round(float(fritura_mean), 3),
                    "mean_cafeteria": round(float(cafe_mean), 3),
                    "type_hierarchy_passed": type_hierarchy_passed,
                    "weekday_mean": round(float(weekday_mean), 3),
                    "weekend_mean": round(float(weekend_mean), 3),
                    "weekend_lift_ratio": round(float(ratio), 3),
                    "weekend_lift_passed": weekend_lift_passed,
                    "passed": bool(type_hierarchy_passed and weekend_lift_passed),
                }

                if not type_hierarchy_passed:
                    results["errors"].append(
                        f"Business type volume hierarchy violated: PicaPollo({pica_mean:.2f}) > Fritura({fritura_mean:.2f}) > Cafeteria({cafe_mean:.2f})"
                    )
                if not weekend_lift_passed:
                    results["errors"].append(
                        f"Dominican weekend surge violated: Weekend/Weekday ratio is {ratio:.2f} (< 1.4 target)."
                    )

            if results["errors"]:
                results["status"] = "FAILED"
                if raise_on_error:
                    raise DataIntegrityError("; ".join(results["errors"]))

            return results

        finally:
            if should_close:
                sess.close()

    def validate_daily_features(self, df: pd.DataFrame, raise_on_error: bool = True) -> Dict[str, Any]:
        """Validate aggregated daily features DataFrame."""
        errors: List[str] = []

        if df.empty:
            errors.append("Feature dataset is completely empty.")
        else:
            required_cols = [
                "date",
                "container_id",
                "business_id",
                "business_name",
                "business_type",
                "num_fryers",
                "avg_daily_customers",
                "day_of_week",
                "is_weekend",
                "lag_7d_liters",
                "daily_liters",
                "is_synthetic",
            ]
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                errors.append(f"Missing required columns: {missing}")

            if "daily_liters" in df.columns and (df["daily_liters"] < 0.0).any():
                errors.append("Negative values detected in daily_liters feature.")

            if "is_synthetic" in df.columns and not df["is_synthetic"].all():
                errors.append("Found non-synthetic records in daily features.")

        results = {
            "status": "FAILED" if errors else "PASSED",
            "errors": errors,
            "total_rows": len(df),
        }

        if errors and raise_on_error:
            raise DataIntegrityError("; ".join(errors))

        return results
