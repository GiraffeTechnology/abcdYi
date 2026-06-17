#!/usr/bin/env python3
"""
GPM Real-Data Availability Test Pipeline — Data Availability Test Runner

Runs simulated price validations against a test batch and produces a structured
test report.

Usage:
    uv run python gpm/scripts/run_data_availability_test.py <batch_id>

Arguments:
    batch_id    The batch_id used when the data was loaded via collect_qwen_data.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gpm.db import AsyncSessionLocal
from gpm.service import get_test_batch_summary, recalculate_benchmarks, validate_price


async def run_test(batch_id: str) -> None:
    reports_dir = Path(__file__).resolve().parents[1] / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"data_availability_report_{batch_id}.json"

    async with AsyncSessionLocal() as session:
        # 1. Get batch summary
        print(f"[run_data_availability_test] Getting batch summary for batch_id={batch_id}")
        summary = await get_test_batch_summary(session, batch_id)

        if summary["total_records"] == 0:
            print(f"ERROR: No records found for batch_id={batch_id}", file=sys.stderr)
            sys.exit(1)

        print(f"  Total records: {summary['total_records']}")
        print(f"  Process IDs: {list(summary['process_breakdown'].keys())}")

        # 2. Recalculate benchmarks for the batch's process_ids
        process_ids = list(summary["process_breakdown"].keys())
        print(f"\n[run_data_availability_test] Recalculating benchmarks for {len(process_ids)} process(es)...")
        benchmark_stats = await recalculate_benchmarks(session, process_ids=process_ids)
        print(f"  Updated benchmarks for: {list(benchmark_stats.keys())}")

        # 3. Run simulated price validations (5 test orders per process_id)
        print(f"\n[run_data_availability_test] Running simulated price validations...")
        validation_results = {}

        for process_id, stat_list in benchmark_stats.items():
            process_results = []
            for stat in stat_list:
                avg = stat["avg_price"]
                std = stat["std_dev"] or 0.0
                param_key = stat["param_key"]

                # Spread 5 test prices across the deviation range
                # Prices: avg-2*std, avg-std, avg, avg+std, avg+2*std
                test_prices = [
                    max(0.01, avg - 2 * std),
                    max(0.01, avg - std),
                    avg,
                    avg + std,
                    avg + 2 * std,
                ]

                param_results = []
                for price in test_prices:
                    result = await validate_price(
                        session,
                        process_id=process_id,
                        unit_price=price,
                        param_key=param_key,
                    )
                    param_results.append({
                        "test_price": round(price, 4),
                        "avg_price": result.avg_price,
                        "deviation_rate": round(result.deviation_rate, 4) if result.deviation_rate is not None else None,
                        "classification": result.classification,
                        "benchmark_found": result.benchmark_found,
                    })

                process_results.append({
                    "param_key": param_key,
                    "avg_price": avg,
                    "std_dev": std,
                    "sample_size": stat["sample_size"],
                    "test_prices": param_results,
                    "benchmark_coverage": "OK" if any(r["benchmark_found"] for r in param_results) else "MISSING",
                })

            validation_results[process_id] = process_results

        # Count benchmark coverage
        total_params = sum(len(v) for v in validation_results.values())
        covered = sum(
            1 for v in validation_results.values()
            for item in v
            if item["benchmark_coverage"] == "OK"
        )

        # 4. Assemble the report
        report = {
            "batch_id": batch_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "benchmark_recalculation": {
                "process_ids_updated": list(benchmark_stats.keys()),
                "total_param_groups": total_params,
            },
            "data_availability": {
                "total_param_groups": total_params,
                "covered_param_groups": covered,
                "coverage_rate": round(covered / total_params, 4) if total_params > 0 else 0.0,
            },
            "validation_results": validation_results,
        }

        # 5. Write report to file
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 6. Print human-readable summary
        print("\n" + "=" * 60)
        print("DATA AVAILABILITY TEST REPORT")
        print("=" * 60)
        print(f"  Batch ID         : {batch_id}")
        print(f"  Generated at     : {report['generated_at']}")
        print(f"  Total records    : {summary['total_records']}")
        print(f"  Process groups   : {len(process_ids)}")
        print(f"  Param groups     : {total_params}")
        print(f"  Covered          : {covered}/{total_params} ({report['data_availability']['coverage_rate']:.1%})")
        print(f"\nProcess breakdown:")
        for pid, count in summary["process_breakdown"].items():
            print(f"    {pid:30s}  {count} records")
        print(f"\nReport saved to: {report_path}")
        print("=" * 60)

        # Commit the benchmarks we upserted
        await session.commit()


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: uv run python gpm/scripts/run_data_availability_test.py <batch_id>",
            file=sys.stderr,
        )
        sys.exit(1)

    batch_id = sys.argv[1]
    asyncio.run(run_test(batch_id))


if __name__ == "__main__":
    main()
