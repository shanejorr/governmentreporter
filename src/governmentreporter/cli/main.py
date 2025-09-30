"""
Main CLI entry point for GovernmentReporter.

This module provides the primary command-line interface using Click.
All commands are organized into subcommands for different operations.
"""

import os
import sys
import click
from .ingest import ingest
from .server import server
from .query import query


def shell_complete_install():
    """Install shell completion for the current shell."""
    shell = os.path.basename(os.environ.get("SHELL", ""))

    if shell in ["bash", "zsh", "fish"]:
        click.echo(f"Installing completion for {shell}...")
        click.echo("\nAdd this to your shell's RC file:\n")

        if shell == "bash":
            click.echo('eval "$(_GOVERNMENTREPORTER_COMPLETE=bash_source governmentreporter)"')
            click.echo("\nFor bash, add to ~/.bashrc or ~/.bash_profile")
        elif shell == "zsh":
            click.echo('eval "$(_GOVERNMENTREPORTER_COMPLETE=zsh_source governmentreporter)"')
            click.echo("\nFor zsh, add to ~/.zshrc")
        elif shell == "fish":
            click.echo('_GOVERNMENTREPORTER_COMPLETE=fish_source governmentreporter | source')
            click.echo("\nFor fish, add to ~/.config/fish/config.fish")

        click.echo("\nThen restart your shell or run: source <your-rc-file>")
    else:
        click.echo(f"Unknown shell: {shell}. Completion supported for bash, zsh, and fish.")
        sys.exit(1)


def shell_complete_show():
    """Show shell completion code for the current shell."""
    shell = os.path.basename(os.environ.get("SHELL", ""))

    if shell == "bash":
        click.echo('eval "$(_GOVERNMENTREPORTER_COMPLETE=bash_source governmentreporter)"')
    elif shell == "zsh":
        click.echo('eval "$(_GOVERNMENTREPORTER_COMPLETE=zsh_source governmentreporter)"')
    elif shell == "fish":
        click.echo('_GOVERNMENTREPORTER_COMPLETE=fish_source governmentreporter | source')
    else:
        click.echo(f"Unknown shell: {shell}. Completion supported for bash, zsh, and fish.")
        sys.exit(1)


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0", prog_name="governmentreporter")
@click.option("--install-completion", is_flag=True, help="Install shell completion")
@click.option("--show-completion", is_flag=True, help="Show shell completion code")
@click.pass_context
def main(ctx, install_completion, show_completion):
    """
    GovernmentReporter - MCP server for US government document search.

    Provides semantic search over Supreme Court opinions and Executive Orders
    using RAG (Retrieval Augmented Generation) with hierarchical chunking.

    \b
    Shell Completion:
        governmentreporter --install-completion    # Install completion
        governmentreporter --show-completion       # Show completion code
    """
    if install_completion:
        shell_complete_install()
        ctx.exit()
    if show_completion:
        shell_complete_show()
        ctx.exit()
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register subcommands
main.add_command(ingest)
main.add_command(server)
main.add_command(query)


if __name__ == "__main__":
    main()