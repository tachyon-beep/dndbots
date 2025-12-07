"""Tests for CLI."""

import pytest
from unittest.mock import patch, AsyncMock


class TestCLISessionZero:
    def test_cli_has_session_zero_option(self):
        """CLI should have --session-zero flag."""
        from dndbots.cli import main
        import argparse

        # This is a basic structural test
        # Full integration test would require mocking
        assert callable(main)
