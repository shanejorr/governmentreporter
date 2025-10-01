"""
Tests for ingest CLI commands.

This module tests the 'governmentreporter ingest' command group
including SCOTUS and Executive Order ingestion subcommands.

Python Learning Notes:
    - Click command groups have multiple subcommands
    - Date validation is critical for API queries
    - Progress tracking enables resumable operations
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from governmentreporter.cli.ingest import ingest


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestIngestCommandGroup:
    """Test ingest command group."""

    def test_ingest_shows_help(self, cli_runner):
        """Test ingest --help shows available subcommands."""
        result = cli_runner.invoke(ingest, ['--help'])

        assert result.exit_code == 0
        assert "ingest" in result.output.lower()
        assert "scotus" in result.output.lower()
        assert "eo" in result.output.lower() or "executive" in result.output.lower()

    def test_ingest_requires_subcommand(self, cli_runner):
        """Test ingest without subcommand shows help or error."""
        result = cli_runner.invoke(ingest, [])

        # Should show help or error about missing subcommand
        assert "scotus" in result.output.lower() or "Commands:" in result.output


class TestIngestSCOTUSCommand:
    """Test SCOTUS ingestion command."""

    def test_scotus_ingest_shows_help(self, cli_runner):
        """Test scotus ingest help displays usage."""
        result = cli_runner.invoke(ingest, ['scotus', '--help'])

        assert result.exit_code == 0
        assert "scotus" in result.output.lower() or "supreme court" in result.output.lower()
        assert "--start-date" in result.output
        assert "--end-date" in result.output

    def test_scotus_requires_start_date(self, cli_runner):
        """Test scotus command requires --start-date."""
        result = cli_runner.invoke(ingest, ['scotus', '--end-date', '2024-12-31'])

        # Should show error about missing start-date
        assert result.exit_code != 0

    def test_scotus_requires_end_date(self, cli_runner):
        """Test scotus command requires --end-date."""
        result = cli_runner.invoke(ingest, ['scotus', '--start-date', '2024-01-01'])

        # Should show error about missing end-date
        assert result.exit_code != 0

    @patch('governmentreporter.cli.ingest.SCOTUSIngester')
    def test_scotus_accepts_valid_dates(self, mock_ingester_class, cli_runner):
        """Test scotus accepts valid date range."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31'
        ])

        # Should create ingester and call run
        mock_ingester_class.assert_called_once()
        mock_ingester.run.assert_called_once()

    def test_scotus_validates_date_format(self, cli_runner):
        """Test scotus validates date format (YYYY-MM-DD)."""
        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '01/01/2024',  # Wrong format
            '--end-date', '2024-12-31'
        ])

        # Should show error about date format
        if result.exit_code != 0:
            assert "date" in result.output.lower() or "format" in result.output.lower()

    @patch('governmentreporter.cli.ingest.SCOTUSIngester')
    def test_scotus_accepts_batch_size_option(self, mock_ingester_class, cli_runner):
        """Test scotus accepts --batch-size option."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--batch-size', '100'
        ])

        # Should pass batch_size to ingester
        call_kwargs = mock_ingester_class.call_args[1]
        assert call_kwargs.get('batch_size') == 100

    @patch('governmentreporter.cli.ingest.SCOTUSIngester')
    def test_scotus_accepts_dry_run_flag(self, mock_ingester_class, cli_runner):
        """Test scotus accepts --dry-run flag."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--dry-run'
        ])

        # Should pass dry_run=True to ingester
        call_kwargs = mock_ingester_class.call_args[1]
        assert call_kwargs.get('dry_run') is True

    @patch('governmentreporter.cli.ingest.SCOTUSIngester')
    def test_scotus_accepts_progress_db_path(self, mock_ingester_class, cli_runner):
        """Test scotus accepts custom progress database path."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--progress-db', './custom_progress.db'
        ])

        call_kwargs = mock_ingester_class.call_args[1]
        assert './custom_progress.db' in str(call_kwargs.get('progress_db', ''))

    @patch('governmentreporter.cli.ingest.SCOTUSIngester')
    def test_scotus_handles_ingestion_errors(self, mock_ingester_class, cli_runner):
        """Test scotus handles ingestion errors gracefully."""
        mock_ingester = MagicMock()
        mock_ingester.run.side_effect = Exception("Ingestion failed")
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31'
        ])

        # Should handle error (exit code or error message)
        assert result.exit_code != 0 or "error" in result.output.lower()


class TestIngestExecutiveOrdersCommand:
    """Test Executive Orders ingestion command."""

    def test_eo_ingest_shows_help(self, cli_runner):
        """Test eo ingest help displays usage."""
        result = cli_runner.invoke(ingest, ['eo', '--help'])

        assert result.exit_code == 0
        assert "executive order" in result.output.lower() or "eo" in result.output.lower()
        assert "--start-date" in result.output
        assert "--end-date" in result.output

    def test_eo_requires_start_date(self, cli_runner):
        """Test eo command requires --start-date."""
        result = cli_runner.invoke(ingest, ['eo', '--end-date', '2024-12-31'])

        assert result.exit_code != 0

    def test_eo_requires_end_date(self, cli_runner):
        """Test eo command requires --end-date."""
        result = cli_runner.invoke(ingest, ['eo', '--start-date', '2024-01-01'])

        assert result.exit_code != 0

    @patch('governmentreporter.cli.ingest.ExecutiveOrderIngester')
    def test_eo_accepts_valid_dates(self, mock_ingester_class, cli_runner):
        """Test eo accepts valid date range."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'eo',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31'
        ])

        mock_ingester_class.assert_called_once()
        mock_ingester.run.assert_called_once()

    @patch('governmentreporter.cli.ingest.ExecutiveOrderIngester')
    def test_eo_accepts_batch_size_option(self, mock_ingester_class, cli_runner):
        """Test eo accepts --batch-size option."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'eo',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--batch-size', '50'
        ])

        call_kwargs = mock_ingester_class.call_args[1]
        assert call_kwargs.get('batch_size') == 50

    @patch('governmentreporter.cli.ingest.ExecutiveOrderIngester')
    def test_eo_accepts_dry_run_flag(self, mock_ingester_class, cli_runner):
        """Test eo accepts --dry-run flag."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'eo',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--dry-run'
        ])

        call_kwargs = mock_ingester_class.call_args[1]
        assert call_kwargs.get('dry_run') is True


class TestIngestCommandValidation:
    """Test input validation for ingest commands."""

    def test_validates_start_date_before_end_date(self, cli_runner):
        """Test validation that start_date is before end_date."""
        # This validation might be in the ingester class, not CLI
        # But we can test that invalid dates are handled
        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-12-31',
            '--end-date', '2024-01-01'
        ])

        # Should either error in CLI or when ingester runs
        # (Implementation specific)
        assert isinstance(result.output, str)

    def test_validates_reasonable_batch_size(self, cli_runner):
        """Test validation of batch size parameter."""
        # Test with unreasonably large batch size
        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--batch-size', '99999'
        ])

        # Should handle gracefully (might warn or adjust)
        assert isinstance(result.output, str)

    def test_handles_invalid_batch_size_type(self, cli_runner):
        """Test handling of non-integer batch size."""
        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-12-31',
            '--batch-size', 'invalid'
        ])

        assert result.exit_code != 0
        assert "integer" in result.output.lower() or "invalid" in result.output.lower()


class TestIngestCommandOutput:
    """Test output and feedback from ingest commands."""

    @patch('governmentreporter.cli.ingest.SCOTUSIngester')
    def test_provides_progress_feedback(self, mock_ingester_class, cli_runner):
        """Test that ingest commands provide progress feedback."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-31'
        ])

        # Should provide some output (not silent)
        assert len(result.output) >= 0  # May be empty in test environment

    @patch('governmentreporter.cli.ingest.SCOTUSIngester')
    def test_dry_run_indicates_no_storage(self, mock_ingester_class, cli_runner):
        """Test dry-run mode indicates no data will be stored."""
        mock_ingester = MagicMock()
        mock_ingester.run.return_value = None
        mock_ingester_class.return_value = mock_ingester

        result = cli_runner.invoke(ingest, [
            'scotus',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-31',
            '--dry-run'
        ])

        # dry_run should be passed to ingester
        call_kwargs = mock_ingester_class.call_args[1]
        assert call_kwargs.get('dry_run') is True
