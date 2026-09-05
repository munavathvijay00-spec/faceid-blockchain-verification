"""Logging and console presentation utilities."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import sys

console = Console()

def print_banner():
    """Prints application header banner."""
    banner_text = Text()
    banner_text.append("╔═══════════════════════════════════════════════════════════════╗\n", style="bold cyan")
    banner_text.append("║           FACE ID + BLOCKCHAIN VERIFICATION PIPELINE          ║\n", style="bold white")
    banner_text.append("║  Detect Face • Reverse Image Search • Tamper-Evident Ledger   ║\n", style="bold yellow")
    banner_text.append("╚═══════════════════════════════════════════════════════════════╝", style="bold cyan")
    console.print(banner_text)

def log_step(step_number: int, title: str, description: str = ""):
    """Logs a major pipeline milestone."""
    header = f"[bold green]STAGE {step_number}:[/bold green] [bold white]{title}[/bold white]"
    if description:
        header += f" - [dim]{description}[/dim]"
    console.print(f"\n{header}")

def log_info(msg: str):
    """Logs informational message."""
    console.print(f" [cyan]ℹ[/cyan] {msg}")

def log_success(msg: str):
    """Logs success message."""
    console.print(f" [bold green]✔[/bold green] {msg}")

def log_warning(msg: str):
    """Logs warning message."""
    console.print(f" [bold yellow]▲[/bold yellow] {msg}")

def log_error(msg: str):
    """Logs error message."""
    console.print(f" [bold red]✖[/bold red] {msg}", file=sys.stderr)

def display_summary_table(data: dict):
    """Renders a rich table summarizing pipeline results."""
    table = Table(title="[bold yellow]Pipeline Execution Summary[/bold yellow]", border_style="cyan")
    table.add_column("Property", style="bold white", width=24)
    table.add_column("Value / Details", style="green")

    for key, value in data.items():
        table.add_row(key, str(value))

    console.print(table)
