#!/usr/bin/env python3
"""
Test script for bulk update API endpoints.

Usage:
    python test_bulk_update_api.py [plan_id]
"""

import json
import sys
from typing import Any, Dict, Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def make_request(
    method: str, url: str, data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Make HTTP request and return JSON response."""
    headers = {"Content-Type": "application/json"}

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Error making request: {e}[/red]")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                console.print(
                    f"[red]Error details: {json.dumps(error_detail, indent=2)}[/red]"
                )
            except Exception:
                console.print(f"[red]Response text: {e.response.text}[/red]")
        return {}


def test_get_endpoint(base_url: str, plan_id: int) -> Dict[str, Any]:
    """Test the GET test endpoint."""
    console.print(
        "\n[bold cyan]1. Testing GET /test/bulk-update-test/{plan_id}[/bold cyan]"
    )

    url = f"{base_url}/test/bulk-update-test/{plan_id}"
    result = make_request("GET", url)

    if result:
        # Display plan info
        if "plan" in result:
            plan = result["plan"]
            console.print(
                Panel(
                    f"[green]Plan ID:[/green] {plan.get('id')}\n"
                    f"[green]Name:[/green] {plan.get('name')}\n"
                    f"[green]Status:[/green] {plan.get('status')}\n"
                    f"[green]Created:[/green] {plan.get('created_at')}",
                    title="Plan Information",
                )
            )

        # Display summary table
        if "summary" in result:
            summary = result["summary"]
            table = Table(title="Change Summary")
            table.add_column("Type", style="cyan")
            table.add_column("Count", style="magenta", justify="right")

            for key, value in summary.items():
                label = key.replace("_", " ").title()
                table.add_row(label, str(value))

            console.print(table)

        # Display changes by field
        if "changes_by_field" in result:
            field_table = Table(title="Changes by Field")
            field_table.add_column("Field", style="cyan")
            field_table.add_column("Total", justify="right")
            field_table.add_column("Pending", justify="right")
            field_table.add_column("Accepted", justify="right")
            field_table.add_column("Rejected", justify="right")
            field_table.add_column("Applied", justify="right")

            for field, counts in result["changes_by_field"].items():
                field_table.add_row(
                    field,
                    str(counts.get("total", 0)),
                    str(counts.get("pending", 0)),
                    str(counts.get("accepted", 0)),
                    str(counts.get("rejected", 0)),
                    str(counts.get("applied", 0)),
                )

            console.print(field_table)

    return result


def test_dry_run(
    base_url: str,
    plan_id: int,
    action: str,
    field: Optional[str] = None,
    confidence_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """Test bulk update with dry run."""
    console.print(
        f"\n[bold cyan]Testing POST /test/bulk-update-test/{plan_id} (dry run - {action})[/bold cyan]"
    )

    url = f"{base_url}/test/bulk-update-test/{plan_id}"
    data = {"action": action, "dry_run": True}

    if field:
        data["field"] = field
    if confidence_threshold is not None:
        data["confidence_threshold"] = confidence_threshold

    result = make_request("POST", url, data)

    if result:
        console.print(f"[yellow]Action:[/yellow] {result.get('action')}")
        console.print(f"[yellow]Dry Run:[/yellow] {result.get('dry_run')}")

        if "filters" in result:
            console.print(
                f"[yellow]Filters:[/yellow] {json.dumps(result['filters'], indent=2)}"
            )

        if "would_affect" in result:
            affect = result["would_affect"]
            console.print(
                f"\n[green]Would affect {affect.get('total_changes', 0)} changes[/green]"
            )

            if "changes_by_field" in affect and affect["changes_by_field"]:
                table = Table(title="Changes by Field")
                table.add_column("Field", style="cyan")
                table.add_column("Count", style="magenta", justify="right")

                for field, count in affect["changes_by_field"].items():
                    table.add_row(field, str(count))

                console.print(table)

    return result


def test_actual_bulk_update(base_url: str, plan_id: int) -> Dict[str, Any]:
    """Test the actual bulk update endpoint."""
    console.print(
        f"\n[bold cyan]Testing POST /analysis/plans/{plan_id}/bulk-update (accept by field - tags)[/bold cyan]"
    )

    url = f"{base_url}/analysis/plans/{plan_id}/bulk-update"
    data = {"action": "accept_by_field", "field": "tags"}

    # First, do a dry run to see what would be affected
    test_url = f"{base_url}/test/bulk-update-test/{plan_id}"
    dry_run_data = {**data, "dry_run": True}
    dry_run_result = make_request("POST", test_url, dry_run_data)

    if dry_run_result and "would_affect" in dry_run_result:
        total_changes = dry_run_result["would_affect"].get("total_changes", 0)
        if total_changes == 0:
            console.print(
                "[yellow]No pending changes to update for tags field[/yellow]"
            )
            return {}
        else:
            console.print(f"[yellow]This will affect {total_changes} changes[/yellow]")

    # Perform the actual update
    result = make_request("POST", url, data)

    if result:
        console.print(
            Panel(
                f"[green]Action:[/green] {result.get('action')}\n"
                f"[green]Updated Count:[/green] {result.get('updated_count')}\n"
                f"[green]Plan Status:[/green] {result.get('plan_status')}\n"
                f"[green]Total Changes:[/green] {result.get('total_changes')}\n"
                f"[green]Applied:[/green] {result.get('applied_changes')}\n"
                f"[green]Rejected:[/green] {result.get('rejected_changes')}\n"
                f"[green]Pending:[/green] {result.get('pending_changes')}",
                title="Bulk Update Result",
            )
        )

    return result


def main():
    """Main test function."""
    # Get plan ID from command line or use default
    plan_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    base_url = "http://localhost:8000/api"

    console.print(
        f"[bold magenta]Testing Bulk Update API for Plan ID: {plan_id}[/bold magenta]"
    )
    console.print("=" * 60)

    # Test 1: Get current state
    get_result = test_get_endpoint(base_url, plan_id)

    if not get_result:
        console.print("[red]Failed to get plan information. Exiting.[/red]")
        return

    # Test 2: Dry run - accept all
    test_dry_run(base_url, plan_id, "accept_all")

    # Test 3: Dry run - accept by field
    test_dry_run(base_url, plan_id, "accept_by_field", field="tags")

    # Test 4: Dry run - accept by confidence
    test_dry_run(base_url, plan_id, "accept_by_confidence", confidence_threshold=0.8)

    # Test 5: Actual bulk update (optional - ask for confirmation)
    console.print(
        "\n[bold yellow]Do you want to perform an actual bulk update? (y/N)[/bold yellow]"
    )
    if input().lower() == "y":
        test_actual_bulk_update(base_url, plan_id)
    else:
        console.print("[yellow]Skipping actual bulk update[/yellow]")

    console.print("\n[bold green]Testing completed![/bold green]")


if __name__ == "__main__":
    main()
