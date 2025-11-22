#!/usr/bin/env python3
"""
UTCP CLI Tool - Command-line interface for UTCP service discovery and testing

Commands:
    utcp discover <url>              - Discover service and show tools
    utcp list-services               - List all registered services
    utcp call <service.tool> <input> - Call a tool directly
    utcp health <service>            - Check service health
    utcp tools <service>             - List tools for a service
    utcp monitor                     - Real-time service monitoring
    utcp test <service>              - Run automated tests

Installation:
    pip install click rich httpx

Usage:
    python -m maestro_core_api.cli.utcp_cli discover http://localhost:8100
    python -m maestro_core_api.cli.utcp_cli call quality-fabric.run-unit-tests '{"project_id": "test"}'
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    import click
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.live import Live
    from rich.layout import Layout
    from rich import box
    import httpx
except ImportError as e:
    print(f"Error: Required dependencies not installed: {e}")
    print("Install with: pip install click rich httpx")
    sys.exit(1)

console = Console()


class UTCPClient:
    """Simple UTCP client for CLI operations."""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

    async def fetch_manual(self, base_url: str) -> Dict[str, Any]:
        """Fetch UTCP manual from service."""
        manual_url = f"{base_url.rstrip('/')}/utcp-manual.json"
        response = await self.http_client.get(manual_url)
        response.raise_for_status()
        return response.json()

    async def list_tools(self, base_url: str) -> Dict[str, Any]:
        """List tools from service."""
        tools_url = f"{base_url.rstrip('/')}/utcp/tools"
        response = await self.http_client.get(tools_url)
        response.raise_for_status()
        return response.json()

    async def check_health(self, base_url: str) -> Dict[str, Any]:
        """Check service health."""
        health_url = f"{base_url.rstrip('/')}/health"
        try:
            response = await self.http_client.get(health_url)
            return {
                "healthy": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}


@click.group()
def cli():
    """UTCP CLI - Tool for service discovery and testing."""
    pass


@cli.command()
@click.argument('url')
@click.option('--json-output', is_flag=True, help='Output as JSON')
def discover(url: str, json_output: bool):
    """Discover UTCP service at URL and show available tools."""
    async def do_discover():
        client = UTCPClient()
        try:
            console.print(f"\n[bold cyan]Discovering service at:[/] {url}\n")

            # Fetch manual
            manual = await client.fetch_manual(url)

            if json_output:
                console.print_json(data=manual)
                return

            # Display service info
            metadata = manual.get("metadata", {})
            console.print(Panel(
                f"[bold green]{metadata.get('name', 'Unknown Service')}[/]\n"
                f"[white]{metadata.get('description', 'No description')}[/]\n\n"
                f"[cyan]Version:[/] {metadata.get('version', 'N/A')}\n"
                f"[cyan]Base URL:[/] {metadata.get('base_url', url)}\n"
                f"[cyan]UTCP Enabled:[/] ✓",
                title="Service Information",
                border_style="green"
            ))

            # Display tools in table
            tools = manual.get("tools", [])
            if tools:
                table = Table(title=f"\nAvailable Tools ({len(tools)})", box=box.ROUNDED)
                table.add_column("Tool Name", style="cyan", no_wrap=True)
                table.add_column("Description", style="white")
                table.add_column("Tags", style="yellow")

                for tool in tools:
                    tags = ", ".join(tool.get("metadata", {}).get("tags", []))
                    table.add_row(
                        tool["name"],
                        tool["description"][:80] + "..." if len(tool["description"]) > 80 else tool["description"],
                        tags
                    )

                console.print(table)

            console.print(f"\n[green]✓[/] Successfully discovered {len(tools)} tools\n")

        except httpx.HTTPError as e:
            console.print(f"\n[red]✗ HTTP Error:[/] {e}\n", style="bold red")
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/] {e}\n", style="bold red")
        finally:
            await client.close()

    asyncio.run(do_discover())


@cli.command()
@click.argument('url')
def tools(url: str):
    """List all tools available from service."""
    async def do_list_tools():
        client = UTCPClient()
        try:
            console.print(f"\n[bold cyan]Fetching tools from:[/] {url}\n")

            tools_data = await client.list_tools(url)

            table = Table(title=f"Tools: {tools_data.get('service', 'Unknown')}", box=box.ROUNDED)
            table.add_column("Tool Name", style="cyan")
            table.add_column("Description", style="white")

            for tool in tools_data.get("tools", []):
                table.add_row(
                    tool["name"],
                    tool["description"][:100] + "..." if len(tool["description"]) > 100 else tool["description"]
                )

            console.print(table)
            console.print(f"\n[green]Total tools:[/] {tools_data.get('tool_count', 0)}\n")

        except Exception as e:
            console.print(f"\n[red]✗ Error:[/] {e}\n", style="bold red")
        finally:
            await client.close()

    asyncio.run(do_list_tools())


@cli.command()
@click.argument('url')
def health(url: str):
    """Check service health."""
    async def do_health_check():
        client = UTCPClient()
        try:
            console.print(f"\n[bold cyan]Checking health:[/] {url}\n")

            health_data = await client.check_health(url)

            if health_data.get("healthy"):
                console.print(Panel(
                    f"[bold green]✓ Service is healthy[/]\n\n"
                    f"Status Code: {health_data.get('status_code')}",
                    title="Health Check",
                    border_style="green"
                ))

                if health_data.get("data"):
                    console.print("\n[bold]Health Data:[/]")
                    console.print_json(data=health_data["data"])
            else:
                console.print(Panel(
                    f"[bold red]✗ Service is unhealthy[/]\n\n"
                    f"Error: {health_data.get('error', 'Unknown error')}",
                    title="Health Check",
                    border_style="red"
                ))

            console.print()

        except Exception as e:
            console.print(f"\n[red]✗ Error:[/] {e}\n", style="bold red")
        finally:
            await client.close()

    asyncio.run(do_health_check())


@cli.command()
@click.argument('tool_name')
@click.argument('input_json')
@click.option('--base-url', default="http://localhost:8100", help='Service base URL')
def call(tool_name: str, input_json: str, base_url: str):
    """Call a UTCP tool directly.

    Example:
        utcp call run-unit-tests '{"project_id": "test"}' --base-url http://localhost:8100
    """
    async def do_call():
        client = UTCPClient()
        try:
            # Parse input JSON
            try:
                tool_input = json.loads(input_json)
            except json.JSONDecodeError as e:
                console.print(f"\n[red]✗ Invalid JSON input:[/] {e}\n", style="bold red")
                return

            console.print(f"\n[bold cyan]Calling tool:[/] {tool_name}")
            console.print(f"[bold cyan]Input:[/]")
            console.print_json(data=tool_input)
            console.print()

            # Call tool via HTTP POST
            url = f"{base_url.rstrip('/')}/{tool_name.lstrip('/')}"
            response = await client.http_client.post(url, json=tool_input)
            response.raise_for_status()

            result = response.json()

            console.print(Panel(
                "[bold green]✓ Tool executed successfully[/]",
                title="Result",
                border_style="green"
            ))
            console.print("\n[bold]Response:[/]")
            console.print_json(data=result)
            console.print()

        except httpx.HTTPError as e:
            console.print(f"\n[red]✗ HTTP Error:[/] {e}\n", style="bold red")
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/] {e}\n", style="bold red")
        finally:
            await client.close()

    asyncio.run(do_call())


@cli.command()
@click.option('--services', '-s', multiple=True, help='Service URLs to monitor')
@click.option('--interval', '-i', default=5, help='Refresh interval in seconds')
def monitor(services: tuple, interval: int):
    """Real-time monitoring of UTCP services.

    Example:
        utcp monitor -s http://localhost:8100 -s http://localhost:8003 -i 5
    """
    if not services:
        console.print("\n[yellow]No services specified. Using defaults...[/]")
        services = ["http://localhost:8100", "http://localhost:8003"]

    async def do_monitor():
        client = UTCPClient()

        console.print(f"\n[bold cyan]Monitoring {len(services)} services (Ctrl+C to stop)[/]\n")

        try:
            while True:
                # Create table
                table = Table(title=f"Service Status", box=box.ROUNDED)
                table.add_column("Service", style="cyan")
                table.add_column("Status", style="white")
                table.add_column("Version", style="yellow")
                table.add_column("Tools", style="green")

                for service_url in services:
                    try:
                        health = await client.check_health(service_url)
                        if health.get("healthy"):
                            try:
                                tools = await client.list_tools(service_url)
                                status = "[green]● Healthy[/]"
                                version = health.get("data", {}).get("version", "N/A")
                                tool_count = str(tools.get("tool_count", 0))
                            except:
                                status = "[yellow]● Degraded[/]"
                                version = "N/A"
                                tool_count = "N/A"
                        else:
                            status = "[red]● Down[/]"
                            version = "N/A"
                            tool_count = "N/A"

                        table.add_row(service_url, status, version, tool_count)

                    except Exception as e:
                        table.add_row(service_url, "[red]● Error[/]", "N/A", str(e)[:20])

                console.clear()
                console.print(f"\n[bold]UTCP Service Monitor[/] - Updated: {asyncio.get_event_loop().time():.0f}\n")
                console.print(table)
                console.print(f"\n[dim]Refreshing every {interval}s... (Ctrl+C to stop)[/]")

                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Monitoring stopped[/]\n")
        finally:
            await client.close()

    asyncio.run(do_monitor())


@cli.command()
def version():
    """Show UTCP CLI version."""
    console.print("\n[bold cyan]UTCP CLI[/] v1.0.0")
    console.print("[dim]Universal Tool Calling Protocol Command-Line Interface[/]\n")


if __name__ == "__main__":
    cli()