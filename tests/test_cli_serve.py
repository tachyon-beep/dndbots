"""Tests for CLI serve command."""

import pytest
import sys
from unittest.mock import patch, MagicMock


class TestServeCommand:
    """Tests for the serve command."""

    def test_serve_function_exists(self):
        """Serve function is importable."""
        from dndbots.cli import serve
        assert callable(serve)

    def test_serve_default_port(self):
        """Serve uses port 8000 by default."""
        # Patch uvicorn.run where it's called (inside serve function)
        with patch("uvicorn.run") as mock_run:
            from dndbots.cli import serve
            serve()
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["port"] == 8000

    def test_serve_custom_port(self):
        """Serve accepts custom port."""
        with patch("uvicorn.run") as mock_run:
            from dndbots.cli import serve
            serve(port=9000)
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["port"] == 9000

    def test_main_serve_subcommand(self):
        """Main accepts 'serve' subcommand."""
        with patch.object(sys, 'argv', ['dndbots', 'serve']):
            with patch('uvicorn.run') as mock_run:
                from dndbots.cli import main
                main()
                # Should have called uvicorn.run
                mock_run.assert_called_once()
