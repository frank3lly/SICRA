"""Chronological dataset exporter generating train/test splits for ML training."""

import argparse
import json
import os
from typing import Any, Dict, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from src.data.aggregator import DailyFeatureAggregator
from src.database.session import SessionLocal, get_engine
from src.models.entities import Telemetry
from src.simulation.engine import MonteCarloSimulator

DEFAULT_OUTPUT_DIR = "data/processed"


class ChronologicalDatasetExporter:
    """Exports chronologically ordered datasets and train/test splits without leakage."""

    def __init__(self, db_session: Optional[Session] = None) -> None:
        """Initialize exporter with optional database session."""
        self.db_session = db_session
        self.aggregator = DailyFeatureAggregator(db_session=db_session)

    def export_chronological_splits(
        self,
        train_ratio: float = 0.8,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        features_df: Optional[pd.DataFrame] = None,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Perform chronological date-based split and save artifacts to disk."""
        sess = session or self.db_session or SessionLocal()
        should_close = sess != self.db_session and session is None

        try:
            # 1. Retrieve or aggregate features
            if features_df is not None:
                df = features_df.copy()
            else:
                # Check if telemetry exists in database; if not, generate synthetic data
                telemetry_count = sess.query(Telemetry.id).count()
                if telemetry_count == 0:
                    sim = MonteCarloSimulator(db_session=sess, seed=42)
                    sim.generate_synthetic_telemetry(days=90, interval_hours=2, to_db=True)

                df = self.aggregator.aggregate_daily_features(session=sess)

            if df.empty:
                raise ValueError("No feature records available to export.")

            os.makedirs(output_dir, exist_ok=True)

            # 2. Chronological date-based train/test splitting
            unique_dates = sorted(df["date"].unique())
            total_dates = len(unique_dates)
            split_idx = max(1, int(total_dates * train_ratio))

            train_dates = set(unique_dates[:split_idx])
            test_dates = set(unique_dates[split_idx:])

            train_df = df[df["date"].isin(train_dates)].sort_values(["date", "container_id"]).reset_index(drop=True)
            test_df = df[df["date"].isin(test_dates)].sort_values(["date", "container_id"]).reset_index(drop=True)

            # Assert strict zero chronological leakage
            if not train_df.empty and not test_df.empty:
                assert max(train_dates) < min(test_dates), "Temporal leakage detected between train and test sets!"

            # 3. Export CSV files
            full_path = os.path.join(output_dir, "daily_oil_generation.csv")
            train_path = os.path.join(output_dir, "train_chronological.csv")
            test_path = os.path.join(output_dir, "test_chronological.csv")
            summary_path = os.path.join(output_dir, "dataset_summary.json")

            df.to_csv(full_path, index=False)
            train_df.to_csv(train_path, index=False)
            test_df.to_csv(test_path, index=False)

            # 4. Generate JSON metadata summary
            summary = {
                "total_records": int(len(df)),
                "train_records": int(len(train_df)),
                "test_records": int(len(test_df)),
                "train_ratio": float(train_ratio),
                "total_calendar_days": int(total_dates),
                "train_calendar_days": int(len(train_dates)),
                "test_calendar_days": int(len(test_dates)),
                "date_range": {
                    "start": str(unique_dates[0]),
                    "end": str(unique_dates[-1]),
                },
                "train_date_range": {
                    "start": str(min(train_dates)),
                    "end": str(max(train_dates)),
                },
                "test_date_range": {
                    "start": str(min(test_dates)) if test_dates else None,
                    "end": str(max(test_dates)) if test_dates else None,
                },
                "mean_daily_liters": round(float(df["daily_liters"].mean()), 3),
                "businesses_count": int(df["business_id"].nunique()) if "business_id" in df.columns else 0,
                "containers_count": int(df["container_id"].nunique()) if "container_id" in df.columns else 0,
                "features": list(df.columns),
            }

            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            return {
                "full_csv": full_path,
                "train_csv": train_path,
                "test_csv": test_path,
                "summary_json": summary_path,
                "summary": summary,
            }

        finally:
            if should_close:
                sess.close()


def main() -> None:
    """CLI entrypoint for dataset exporter."""
    parser = argparse.ArgumentParser(
        description="SICRA Chronological ML Dataset Exporter"
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Proportion of oldest consecutive dates allocated to training (default: 0.8)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Destination directory for processed dataset artifacts (default: data/processed/)",
    )
    args = parser.parse_args()

    print(f"Exporting chronological splits (train_ratio={args.train_ratio}) to '{args.output_dir}'...")
    exporter = ChronologicalDatasetExporter()
    result = exporter.export_chronological_splits(
        train_ratio=args.train_ratio,
        output_dir=args.output_dir,
    )
    summary = result["summary"]
    print("Dataset export completed successfully:")
    print(f"  Total records:    {summary['total_records']:,}")
    print(f"  Train set:        {summary['train_records']:,} rows [{summary['train_date_range']['start']} to {summary['train_date_range']['end']}]")
    if summary['test_date_range']['start']:
        print(f"  Test set:         {summary['test_records']:,} rows [{summary['test_date_range']['start']} to {summary['test_date_range']['end']}]")
    print(f"  Summary saved to: {result['summary_json']}")


if __name__ == "__main__":
    main()
