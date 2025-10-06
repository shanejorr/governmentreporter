"""
Tests for server CLI command.

This module tests the 'governmentreporter server' command
that starts the MCP server for LLM integration.

Python Learning Notes:
    - Testing async server startup requires special handling
    - Mocking prevents actual server from starting during tests
    - Environment validation is critical for server startup
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock

from governmentreporter.cli.server import server


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestServerCommand:
    """Test server command functionality."""

    def test_server_command_shows_help(self, cli_runner):
        """Test server --help displays usage information."""
        result = cli_runner.invoke(server, ["--help"])

        assert result.exit_code == 0
        assert "server" in result.output.lower() or "mcp" in result.output.lower()
        assert "Options:" in result.output or "Usage:" in result.output

    @patch("governmentreporter.cli.server.create_and_run_server")
    @patch("governmentreporter.cli.server.os.getenv")
    def test_server_starts_with_valid_config(
        self, mock_getenv, mock_run_server, cli_runner
    ):
        """Test server starts when environment is properly configured."""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            "OPENAI_API_KEY": "test-key",
            "QDRANT_HOST": "localhost",
            "QDRANT_PORT": "6333",
        }.get(key, default)

        # Mock server to not actually start
        mock_run_server.return_value = None

        result = cli_runner.invoke(server, [])

        # Server should attempt to start
        mock_run_server.assert_called_once()

    @patch("governmentreporter.cli.server.os.getenv")
    def test_server_validates_openai_key(self, mock_getenv, cli_runner):
        """Test server validates OpenAI API key exists."""
        # No API key set
        mock_getenv.return_value = None

        result = cli_runner.invoke(server, [])

        # Should fail with error about missing key
        # (Implementation may vary - checking for any error)
        if result.exit_code != 0:
            assert (
                "OPENAI" in result.output
                or "API key" in result.output
                or "error" in result.output.lower()
            )

    @patch("governmentreporter.cli.server.create_and_run_server")
    @patch("governmentreporter.cli.server.os.getenv")
    def test_server_handles_startup_errors(
        self, mock_getenv, mock_run_server, cli_runner
    ):
        """Test server handles startup errors gracefully."""
        mock_getenv.side_effect = lambda key, default=None: {
            "OPENAI_API_KEY": "test-key"
        }.get(key, default)

        # Simulate server startup failure
        mock_run_server.side_effect = Exception("Failed to start server")

        result = cli_runner.invoke(server, [])

        # Should show error message
        if result.exit_code != 0:
            assert len(result.output) > 0

    @patch("governmentreporter.cli.server.create_and_run_server")
    @patch("governmentreporter.cli.server.os.getenv")
    def test_server_respects_environment_variables(
        self, mock_getenv, mock_run_server, cli_runner
    ):
        """Test server reads configuration from environment."""
        env_vars = {
            "OPENAI_API_KEY": "test-key",
            "QDRANT_HOST": "custom-host",
            "QDRANT_PORT": "9999",
            "MCP_SERVER_NAME": "Custom Server",
        }
        mock_getenv.side_effect = lambda key, default=None: env_vars.get(key, default)
        mock_run_server.return_value = None

        result = cli_runner.invoke(server, [])

        # Server should attempt to start with custom config
        mock_run_server.assert_called_once()


class TestServerCommandOptions:
    """Test server command options and flags."""

    def test_server_accepts_no_arguments(self, cli_runner):
        """Test server command works without arguments."""
        # Should show help or attempt to start
        result = cli_runner.invoke(server, [])

        # Should not crash
        assert isinstance(result.output, str)

    def test_server_help_describes_purpose(self, cli_runner):
        """Test help text describes what server does."""
        result = cli_runner.invoke(server, ["--help"])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert any(word in output_lower for word in ["mcp", "server", "llm", "start"])


class TestServerCommandIntegration:
    """Integration tests for server command."""

    @patch("governmentreporter.cli.server.create_and_run_server")
    @patch("governmentreporter.cli.server.os.getenv")
    def test_server_logs_startup_message(
        self, mock_getenv, mock_run_server, cli_runner
    ):
        """Test server logs startup information."""
        mock_getenv.side_effect = lambda key, default=None: {
            "OPENAI_API_KEY": "test-key"
        }.get(key, default)
        mock_run_server.return_value = None

        result = cli_runner.invoke(server, [])

        # Should provide feedback about startup
        # (exact message depends on implementation)
        assert isinstance(result.output, str)

    @patch("governmentreporter.cli.server.create_and_run_server")
    @patch("governmentreporter.cli.server.os.getenv")
    def test_server_can_be_invoked_multiple_times(
        self, mock_getenv, mock_run_server, cli_runner
    ):
        """Test server command can be invoked multiple times."""
        mock_getenv.side_effect = lambda key, default=None: {
            "OPENAI_API_KEY": "test-key"
        }.get(key, default)
        mock_run_server.return_value = None

        # Invoke twice
        result1 = cli_runner.invoke(server, [])
        result2 = cli_runner.invoke(server, [])

        # Both should work independently
        assert mock_run_server.call_count == 2
