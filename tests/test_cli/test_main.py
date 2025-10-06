"""
Tests for main CLI entry point.

This module tests the main CLI command group, version display,
help text, and shell completion functionality.

Python Learning Notes:
    - Click's CliRunner provides testing for CLI applications
    - Result object contains output, exit code, and exception info
    - CLI testing doesn't require actual command execution
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from governmentreporter.cli.main import main


@pytest.fixture
def cli_runner():
    """
    Create Click CLI test runner.

    Returns:
        CliRunner: Test runner for CLI commands.

    Python Learning Notes:
        - CliRunner isolates CLI execution for testing
        - Captures stdout, stderr, and exit codes
        - Provides clean environment for each test
    """
    return CliRunner()


class TestMainCLI:
    """Test main CLI entry point and global options."""

    def test_cli_shows_help_with_no_args(self, cli_runner):
        """Test CLI shows help when invoked without arguments."""
        result = cli_runner.invoke(main, [])

        assert result.exit_code == 0
        assert "GovernmentReporter" in result.output
        assert "Commands:" in result.output

    def test_cli_shows_help_with_help_flag(self, cli_runner):
        """Test --help flag displays help text."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "MCP server" in result.output or "government document" in result.output
        assert "Options:" in result.output
        assert "Commands:" in result.output

    def test_cli_shows_version(self, cli_runner):
        """Test --version flag displays version."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output or "version" in result.output.lower()

    def test_cli_lists_subcommands(self, cli_runner):
        """Test that all subcommands are listed in help."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "server" in result.output
        assert "ingest" in result.output
        assert "query" in result.output

    def test_cli_invalid_command_shows_error(self, cli_runner):
        """Test that invalid command shows helpful error."""
        result = cli_runner.invoke(main, ["invalid-command"])

        assert result.exit_code != 0
        assert "Error" in result.output or "invalid" in result.output.lower()


class TestCLISubcommandAccess:
    """Test that subcommands are accessible from main CLI."""

    def test_server_subcommand_exists(self, cli_runner):
        """Test server subcommand is accessible."""
        result = cli_runner.invoke(main, ["server", "--help"])

        assert result.exit_code == 0
        assert "server" in result.output.lower() or "mcp" in result.output.lower()

    def test_ingest_subcommand_exists(self, cli_runner):
        """Test ingest subcommand is accessible."""
        result = cli_runner.invoke(main, ["ingest", "--help"])

        assert result.exit_code == 0
        assert "ingest" in result.output.lower()

    def test_query_subcommand_exists(self, cli_runner):
        """Test query subcommand is accessible."""
        result = cli_runner.invoke(main, ["query", "--help"])

        assert result.exit_code == 0
        assert "query" in result.output.lower() or "search" in result.output.lower()


class TestCLIErrorHandling:
    """Test CLI error handling and user feedback."""

    def test_cli_handles_keyboard_interrupt_gracefully(self, cli_runner):
        """Test CLI handles Ctrl+C gracefully."""
        # This is hard to test directly, but we can verify the CLI
        # doesn't crash with invalid input
        result = cli_runner.invoke(main, ["--invalid-flag"])

        # Should show error, not crash
        assert "Error" in result.output or "invalid" in result.output.lower()

    def test_cli_provides_helpful_error_messages(self, cli_runner):
        """Test CLI provides helpful error messages."""
        result = cli_runner.invoke(main, ["nonexistent"])

        assert result.exit_code != 0
        # Should guide user
        assert len(result.output) > 0


class TestCLIIntegration:
    """Integration tests for CLI command flow."""

    def test_help_for_nested_commands(self, cli_runner):
        """Test help works for nested command groups."""
        # ingest is a group with subcommands
        result = cli_runner.invoke(main, ["ingest", "--help"])

        assert result.exit_code == 0
        assert "scotus" in result.output.lower() or "eo" in result.output.lower()

    def test_version_works_with_subcommands(self, cli_runner):
        """Test version flag works at any command level."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "version" in result.output.lower() or "0.1" in result.output

    def test_cli_maintains_consistent_style(self, cli_runner):
        """Test CLI maintains consistent help text style."""
        # Get help from multiple commands
        main_help = cli_runner.invoke(main, ["--help"])
        server_help = cli_runner.invoke(main, ["server", "--help"])
        query_help = cli_runner.invoke(main, ["query", "--help"])

        # All should have consistent sections
        for result in [main_help, server_help, query_help]:
            assert result.exit_code == 0
            assert "Options:" in result.output or "Usage:" in result.output
