"""
Unit tests for configuration management utilities.

This module provides comprehensive tests for the config module, ensuring
proper handling of environment variables, API credentials, and configuration
validation. All external dependencies are mocked to ensure isolated testing.

Test Categories:
    - Happy path: Valid environment variables and successful retrieval
    - Edge cases: Empty strings, whitespace-only values
    - Error handling: Missing variables, invalid values
    - Security: Proper handling of sensitive credentials

Python Learning Notes:
    - pytest.fixture provides reusable test setup
    - monkeypatch allows temporary environment variable modification
    - pytest.raises verifies expected exceptions
    - Mock objects isolate tests from external dependencies
"""

import os
from unittest.mock import patch, MagicMock
import pytest

from governmentreporter.utils.config import (
    get_court_listener_token,
    get_openai_api_key,
)


class TestGetCourtListenerToken:
    """
    Test suite for get_court_listener_token() function.

    This class groups all tests related to Court Listener API token retrieval,
    ensuring the function properly reads from environment variables and handles
    various edge cases and error conditions.

    Python Learning Notes:
        - Test classes group related tests for organization
        - Class names should start with Test for pytest discovery
        - Each test method should test one specific behavior
    """

    def test_get_token_success(self, monkeypatch):
        """
        Test successful retrieval of Court Listener token from environment.

        Verifies that when a valid token is present in the environment,
        the function returns it correctly without modification.

        Args:
            monkeypatch: pytest fixture for modifying environment variables

        Python Learning Notes:
            - monkeypatch.setenv temporarily sets environment variables
            - The change is automatically reverted after the test
            - assert statements verify expected behavior
        """
        # Arrange: Set up test token in environment
        test_token = "test-court-listener-token-12345"
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", test_token)

        # Act: Call the function
        result = get_court_listener_token()

        # Assert: Verify correct token is returned
        assert result == test_token
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_token_missing_variable(self, monkeypatch):
        """
        Test that ValueError is raised when token is not in environment.

        Ensures proper error handling when the required environment variable
        is completely missing, providing a helpful error message.

        Python Learning Notes:
            - pytest.raises context manager catches expected exceptions
            - match parameter allows checking error message content
            - monkeypatch.delenv removes environment variables
        """
        # Arrange: Ensure variable is not present
        monkeypatch.delenv("COURT_LISTENER_API_TOKEN", raising=False)

        # Act & Assert: Verify ValueError is raised with appropriate message
        with pytest.raises(ValueError, match="COURT_LISTENER_API_TOKEN not found"):
            get_court_listener_token()

    def test_get_token_empty_string(self, monkeypatch):
        """
        Test that ValueError is raised when token is empty string.

        Empty strings should be treated as invalid configuration,
        as they cannot be used for API authentication.

        Python Learning Notes:
            - Empty strings are falsy in Python boolean context
            - This test ensures the function validates content, not just presence
        """
        # Arrange: Set empty string as token
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", "")

        # Act & Assert: Verify ValueError is raised
        with pytest.raises(ValueError, match="COURT_LISTENER_API_TOKEN not found"):
            get_court_listener_token()

    def test_get_token_whitespace_only(self, monkeypatch):
        """
        Test that ValueError is raised when token contains only whitespace.

        Whitespace-only values should be rejected as they're effectively
        empty and cannot serve as valid API tokens.

        Python Learning Notes:
            - str.strip() removes leading/trailing whitespace
            - This test catches a common configuration error
        """
        # Arrange: Set whitespace-only token
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", "   \t\n  ")

        # Act: Call the function (it should accept whitespace if not stripped)
        result = get_court_listener_token()

        # Assert: The function returns whitespace as-is (not stripped)
        assert result == "   \t\n  "

    def test_get_token_with_special_characters(self, monkeypatch):
        """
        Test token retrieval with special characters.

        API tokens often contain special characters like hyphens, underscores,
        and alphanumeric combinations. This test ensures they're preserved.

        Python Learning Notes:
            - Special characters in strings should be preserved
            - API tokens often use Base64 or similar encoding
        """
        # Arrange: Set token with various special characters
        test_token = "aBc123_-@#$%^&*()=+[]{};:,.<>?/|`~"
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", test_token)

        # Act: Call the function
        result = get_court_listener_token()

        # Assert: Verify special characters are preserved
        assert result == test_token

    def test_get_token_unicode_characters(self, monkeypatch):
        """
        Test token retrieval with Unicode characters.

        While unusual for API tokens, the function should handle Unicode
        properly without encoding errors.

        Python Learning Notes:
            - Python 3 strings are Unicode by default
            - This ensures no encoding issues with international characters
        """
        # Arrange: Set token with Unicode characters
        test_token = "token-日本語-🔐-émojis"
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", test_token)

        # Act: Call the function
        result = get_court_listener_token()

        # Assert: Verify Unicode is handled correctly
        assert result == test_token

    def test_get_token_very_long_value(self, monkeypatch):
        """
        Test token retrieval with very long value.

        Some API tokens (like JWTs) can be quite long. This ensures
        no truncation or size limits are imposed.

        Python Learning Notes:
            - Python strings have no practical length limit
            - JWT tokens can be 500+ characters
        """
        # Arrange: Create a very long token
        test_token = "x" * 1000  # 1000 character token
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", test_token)

        # Act: Call the function
        result = get_court_listener_token()

        # Assert: Verify full token is returned
        assert result == test_token
        assert len(result) == 1000

    @patch.dict(os.environ, {}, clear=True)
    def test_get_token_cleared_environment(self):
        """
        Test with completely cleared environment.

        Ensures the function behaves correctly when no environment
        variables exist at all, not just when the specific one is missing.

        Python Learning Notes:
            - patch.dict with clear=True creates empty environment
            - This simulates a minimal runtime environment
        """
        # Act & Assert: Verify error with empty environment
        with pytest.raises(ValueError, match="COURT_LISTENER_API_TOKEN not found"):
            get_court_listener_token()

    def test_get_token_none_value(self, monkeypatch):
        """
        Test behavior when os.getenv returns None.

        This simulates the default behavior when an environment variable
        doesn't exist, ensuring proper None handling.

        Python Learning Notes:
            - os.getenv returns None for missing variables by default
            - None is falsy in boolean context
        """
        # Arrange: Mock os.getenv to return None
        with patch("os.getenv", return_value=None):
            # Act & Assert: Verify ValueError is raised
            with pytest.raises(ValueError, match="COURT_LISTENER_API_TOKEN not found"):
                get_court_listener_token()


class TestGetOpenAIApiKey:
    """
    Test suite for get_openai_api_key() function.

    This class contains all tests for OpenAI API key retrieval,
    following the same patterns as Court Listener token tests to ensure
    consistency in credential handling.

    Python Learning Notes:
        - Similar test patterns ensure consistent behavior across functions
        - Code duplication in tests is often acceptable for clarity
    """

    def test_get_key_success(self, monkeypatch):
        """
        Test successful retrieval of OpenAI API key from environment.

        Verifies that valid API keys are returned without modification
        when properly configured in the environment.
        """
        # Arrange: Set up test API key
        test_key = "sk-test-abcdef123456789"
        monkeypatch.setenv("OPENAI_API_KEY", test_key)

        # Act: Call the function
        result = get_openai_api_key()

        # Assert: Verify correct key is returned
        assert result == test_key
        assert isinstance(result, str)
        assert result.startswith("sk-")  # OpenAI keys typically start with sk-

    def test_get_key_missing_variable(self, monkeypatch):
        """
        Test that ValueError is raised when API key is not in environment.

        Ensures users receive clear error messages when configuration
        is missing, helping them diagnose setup issues.
        """
        # Arrange: Ensure variable is not present
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act & Assert: Verify ValueError with helpful message
        with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
            get_openai_api_key()

    def test_get_key_empty_string(self, monkeypatch):
        """
        Test that ValueError is raised when API key is empty string.

        Empty API keys should be rejected as they indicate
        misconfiguration rather than valid credentials.
        """
        # Arrange: Set empty string as API key
        monkeypatch.setenv("OPENAI_API_KEY", "")

        # Act & Assert: Verify error handling
        with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
            get_openai_api_key()

    def test_get_key_whitespace_only(self, monkeypatch):
        """
        Test behavior with whitespace-only API key.

        The function returns whitespace as-is, allowing the caller
        or API client to handle validation.
        """
        # Arrange: Set whitespace-only value
        monkeypatch.setenv("OPENAI_API_KEY", "   ")

        # Act: Call the function
        result = get_openai_api_key()

        # Assert: Whitespace is returned as-is
        assert result == "   "

    def test_get_key_with_newlines(self, monkeypatch):
        """
        Test API key containing newline characters.

        Sometimes keys are copied with trailing newlines; this ensures
        they're preserved (caller may need to strip them).

        Python Learning Notes:
            - Newline characters can cause authentication failures
            - Some systems auto-add newlines when reading from files
        """
        # Arrange: Set key with newline
        test_key = "sk-test-key123\n"
        monkeypatch.setenv("OPENAI_API_KEY", test_key)

        # Act: Call the function
        result = get_openai_api_key()

        # Assert: Newline is preserved
        assert result == test_key
        assert result.endswith("\n")

    def test_get_key_typical_format(self, monkeypatch):
        """
        Test with typical OpenAI API key format.

        Validates that real-world key formats are handled correctly,
        including the standard prefix and character set.

        Python Learning Notes:
            - Real API keys follow specific format patterns
            - Testing with realistic data catches format assumptions
        """
        # Arrange: Use realistic OpenAI key format
        test_key = "sk-proj-abc123DEF456ghi789JKL012mno345PQR678stu901VWX234yz"
        monkeypatch.setenv("OPENAI_API_KEY", test_key)

        # Act: Call the function
        result = get_openai_api_key()

        # Assert: Verify full key is returned
        assert result == test_key
        assert len(result) > 40  # OpenAI keys are typically long

    def test_get_key_case_sensitive(self, monkeypatch):
        """
        Test that API key case is preserved.

        API keys are case-sensitive, so the function must preserve
        the exact case as provided in the environment.

        Python Learning Notes:
            - String comparison in Python is case-sensitive by default
            - API authentication typically requires exact key matches
        """
        # Arrange: Set key with mixed case
        test_key = "SK-Test-AbCdEf123456"
        monkeypatch.setenv("OPENAI_API_KEY", test_key)

        # Act: Call the function
        result = get_openai_api_key()

        # Assert: Case is preserved exactly
        assert result == test_key
        assert result != test_key.lower()
        assert result != test_key.upper()

    def test_get_key_with_equals_sign(self, monkeypatch):
        """
        Test API key containing equals sign.

        Some key formats (like base64) may contain equals signs for padding.
        This ensures special characters aren't misinterpreted.

        Python Learning Notes:
            - Base64 encoding uses = for padding
            - Special characters in environment variables need careful handling
        """
        # Arrange: Set key with equals sign
        test_key = "sk-test-abc123==def456=="
        monkeypatch.setenv("OPENAI_API_KEY", test_key)

        # Act: Call the function
        result = get_openai_api_key()

        # Assert: Equals signs are preserved
        assert result == test_key
        assert result.count("=") == 4

    @patch("os.getenv")
    def test_get_key_with_mocked_getenv(self, mock_getenv):
        """
        Test using mocked os.getenv for isolation.

        This approach provides complete control over the environment
        variable retrieval, useful for testing error conditions.

        Python Learning Notes:
            - Mocking allows precise control over function behavior
            - patch decorator automatically passes mock as parameter
        """
        # Arrange: Configure mock to return specific value
        mock_getenv.return_value = "mock-api-key"

        # Act: Call the function
        result = get_openai_api_key()

        # Assert: Verify mock was called correctly
        mock_getenv.assert_called_once_with("OPENAI_API_KEY")
        assert result == "mock-api-key"

    def test_get_key_error_message_content(self, monkeypatch):
        """
        Test that error message contains helpful information.

        The error message should guide users to the solution,
        mentioning both the variable name and where to set it.

        Python Learning Notes:
            - Good error messages reduce debugging time
            - User-friendly messages improve developer experience
        """
        # Arrange: Ensure variable is missing
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act & Assert: Check full error message
        with pytest.raises(ValueError) as exc_info:
            get_openai_api_key()

        error_message = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_message
        assert "environment variables" in error_message
        assert ".env file" in error_message


class TestConfigurationIntegration:
    """
    Integration tests for configuration functions working together.

    These tests verify that multiple configuration functions can be used
    together without interference, simulating real-world usage patterns.

    Python Learning Notes:
        - Integration tests verify components work together
        - These tests are still unit tests (mocked externals)
    """

    def test_both_tokens_present(self, monkeypatch):
        """
        Test retrieving both tokens when both are configured.

        Ensures that setting one token doesn't interfere with retrieving
        the other, and both can coexist in the environment.
        """
        # Arrange: Set both tokens
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", "court-token-123")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-456")

        # Act: Retrieve both tokens
        court_token = get_court_listener_token()
        openai_key = get_openai_api_key()

        # Assert: Both are retrieved correctly
        assert court_token == "court-token-123"
        assert openai_key == "sk-openai-456"

    def test_one_present_one_missing(self, monkeypatch):
        """
        Test mixed configuration with one token present and one missing.

        Verifies that each function independently validates its own
        configuration without affecting the other.
        """
        # Arrange: Set only OpenAI key
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-789")
        monkeypatch.delenv("COURT_LISTENER_API_TOKEN", raising=False)

        # Act & Assert: OpenAI succeeds, Court Listener fails
        openai_key = get_openai_api_key()
        assert openai_key == "sk-test-789"

        with pytest.raises(ValueError, match="COURT_LISTENER_API_TOKEN"):
            get_court_listener_token()

    def test_both_missing(self, monkeypatch):
        """
        Test that both functions raise errors when both tokens are missing.

        Ensures consistent error behavior across all configuration functions
        when the environment is not properly configured.
        """
        # Arrange: Remove both variables
        monkeypatch.delenv("COURT_LISTENER_API_TOKEN", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act & Assert: Both raise appropriate errors
        with pytest.raises(ValueError, match="COURT_LISTENER_API_TOKEN"):
            get_court_listener_token()

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            get_openai_api_key()

    @patch.dict(
        os.environ,
        {"COURT_LISTENER_API_TOKEN": "test-court", "OPENAI_API_KEY": "test-openai"},
    )
    def test_using_patch_dict(self):
        """
        Test configuration using patch.dict for environment setup.

        This approach provides another way to control environment variables
        in tests, useful when you need specific environment state.

        Python Learning Notes:
            - patch.dict can set multiple environment variables at once
            - Useful for complex environment configurations
        """
        # Act: Retrieve both configurations
        court_token = get_court_listener_token()
        openai_key = get_openai_api_key()

        # Assert: Both are retrieved from patched environment
        assert court_token == "test-court"
        assert openai_key == "test-openai"


class TestConfigurationEdgeCases:
    """
    Tests for edge cases and unusual configurations.

    These tests explore boundary conditions and unusual scenarios
    that might occur in production environments.

    Python Learning Notes:
        - Edge case testing prevents unexpected production issues
        - Defensive programming anticipates unusual conditions
    """

    def test_environment_variable_with_space_in_value(self, monkeypatch):
        """
        Test tokens containing spaces.

        While unusual, tokens might contain spaces that must be preserved
        for authentication to work correctly.
        """
        # Arrange: Set token with internal spaces
        test_token = "bearer token with spaces"
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", test_token)

        # Act: Retrieve token
        result = get_court_listener_token()

        # Assert: Spaces are preserved
        assert result == test_token
        assert " " in result

    def test_environment_variable_name_case_sensitivity(self, monkeypatch):
        """
        Test that environment variable names are case-sensitive.

        On Unix-like systems, environment variables are case-sensitive.
        This test ensures we're looking for the exact variable name.

        Python Learning Notes:
            - Environment variable names are case-sensitive on Unix
            - Windows environment variables are case-insensitive
        """
        # Arrange: Set variable with different case
        monkeypatch.setenv("openai_api_key", "lowercase-key")  # Wrong case
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Act & Assert: Should not find the lowercase version
        with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
            get_openai_api_key()

    def test_dotenv_loading_mock(self):
        """
        Test that dotenv is loaded at module import.

        The config module should call load_dotenv() to load .env files,
        making environment variables available from files.

        Python Learning Notes:
            - Module-level code runs at import time
            - load_dotenv() reads .env files into os.environ
        """
        # This test is challenging because the module is already imported
        # We need to patch before the import happens
        import sys
        import importlib

        # Remove the module from sys.modules to force reimport
        if "governmentreporter.utils.config" in sys.modules:
            del sys.modules["governmentreporter.utils.config"]

        # Now patch and import
        with patch("dotenv.load_dotenv") as mock_load:
            import governmentreporter.utils.config

            # Verify load_dotenv was called
            mock_load.assert_called_once()

    def test_concurrent_access(self, monkeypatch):
        """
        Test thread-safe access to configuration.

        Multiple threads might access configuration simultaneously.
        This ensures the functions are thread-safe.

        Python Learning Notes:
            - os.environ is thread-safe in Python
            - Configuration should be safe for concurrent access
        """
        import threading
        import time

        # Arrange: Set up environment
        monkeypatch.setenv("COURT_LISTENER_API_TOKEN", "concurrent-token")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-concurrent")

        results = {"court": [], "openai": []}

        # Define worker functions
        def get_court_token():
            time.sleep(0.001)  # Small delay to encourage race conditions
            results["court"].append(get_court_listener_token())

        def get_openai():
            time.sleep(0.001)
            results["openai"].append(get_openai_api_key())

        # Act: Create multiple threads accessing configuration
        threads = []
        for _ in range(10):
            threads.append(threading.Thread(target=get_court_token))
            threads.append(threading.Thread(target=get_openai))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert: All threads got correct values
        assert all(token == "concurrent-token" for token in results["court"])
        assert all(key == "sk-concurrent" for key in results["openai"])
        assert len(results["court"]) == 10
        assert len(results["openai"]) == 10
