#!/usr/bin/env python3
"""
Example demonstrating the improved configuration pattern in GovernmentReporter.

This script shows how to use the factory function pattern for configuration,
which provides better testability and flexibility compared to module-level singletons.
"""

from governmentreporter.server.config import ServerConfig, get_config, set_config


def main():
    """Demonstrate configuration usage patterns."""

    print("=" * 60)
    print("GovernmentReporter Configuration Examples")
    print("=" * 60)

    # Example 1: Using the default configuration
    print("\n1. Using default configuration:")
    config = get_config()
    print(f"   Server name: {config.server_name}")
    print(f"   Default search limit: {config.default_search_limit}")

    # Example 2: Singleton pattern - all calls return same instance
    print("\n2. Singleton pattern demonstration:")
    config2 = get_config()
    print(f"   Same instance? {config is config2}")

    # Example 3: Custom configuration for testing
    print("\n3. Custom configuration for testing:")
    test_config = ServerConfig(
        server_name="Test Server",
        default_search_limit=20,
        enable_caching=False
    )
    set_config(test_config)

    config3 = get_config()
    print(f"   Server name: {config3.server_name}")
    print(f"   Default search limit: {config3.default_search_limit}")
    print(f"   Caching enabled: {config3.enable_caching}")

    # Example 4: Resetting configuration
    print("\n4. Resetting configuration:")
    fresh_config = get_config(reset=True)
    print(f"   Server name back to: {fresh_config.server_name}")
    print(f"   New instance? {fresh_config is not config3}")

    # Example 5: Configuration for different environments
    print("\n5. Environment-specific configuration:")

    def get_environment_config(env: str) -> ServerConfig:
        """Get configuration for specific environment."""
        if env == "production":
            return ServerConfig(
                server_name="GovernmentReporter Production",
                enable_caching=True,
                log_level="WARNING",
                rate_limit_enabled=True
            )
        elif env == "development":
            return ServerConfig(
                server_name="GovernmentReporter Dev",
                enable_caching=False,
                log_level="DEBUG",
                rate_limit_enabled=False
            )
        else:
            return ServerConfig()  # Default

    dev_config = get_environment_config("development")
    print(f"   Development - Log level: {dev_config.log_level}")
    print(f"   Development - Rate limiting: {dev_config.rate_limit_enabled}")

    prod_config = get_environment_config("production")
    print(f"   Production - Log level: {prod_config.log_level}")
    print(f"   Production - Rate limiting: {prod_config.rate_limit_enabled}")

    print("\n" + "=" * 60)
    print("Configuration examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()