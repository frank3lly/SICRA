"""Command-line interface for the Monte Carlo probabilistic telemetry simulator."""

import argparse
import time
from typing import Optional

from src.simulation.engine import MonteCarloSimulator


def run_simulation(
    days: int = 90,
    interval_hours: int = 2,
    seed: int = 42,
    to_db: bool = True,
    output_csv: Optional[str] = None,
) -> int:
    """Execute simulation engine and print execution metrics."""
    start_time = time.perf_counter()
    print(f"Starting Monte Carlo Simulation [seed={seed}, days={days}, interval={interval_hours}h]...")

    simulator = MonteCarloSimulator(seed=seed)
    records = simulator.generate_synthetic_telemetry(
        days=days,
        interval_hours=interval_hours,
        to_db=to_db,
        output_csv=output_csv,
    )

    elapsed = time.perf_counter() - start_time
    count = len(records)
    print(f"Simulation completed successfully:")
    print(f"  Total records generated: {count:,}")
    print(f"  Execution time:          {elapsed:.2f} seconds")
    print(f"  Throughput:              {int(count / max(0.001, elapsed)):,} records/second")
    if to_db:
        print("  Database status:         Persisted to 'telemetries' table")
    if output_csv:
        print(f"  CSV export status:       Saved to '{output_csv}'")

    return count


def main() -> None:
    """CLI entry point for simulator command."""
    parser = argparse.ArgumentParser(
        description="SICRA Monte Carlo Probabilistic Telemetry Simulation Generator"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of operational days to simulate (default: 90)",
    )
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=2,
        help="Periodic sensor reading frequency in hours (default: 2)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random generator seed for mathematical reproducibility (default: 42)",
    )
    parser.add_argument(
        "--to-db",
        dest="to_db",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Persist generated records into database telemetries table (default: True)",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Optional destination path for standalone CSV export",
    )

    args = parser.parse_args()

    run_simulation(
        days=args.days,
        interval_hours=args.interval_hours,
        seed=args.seed,
        to_db=args.to_db,
        output_csv=args.output_csv,
    )


if __name__ == "__main__":
    main()
