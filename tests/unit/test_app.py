from unittest.mock import MagicMock

import pytest
from fastapi import Request, status
from sqlalchemy.exc import IntegrityError

from src.app import integrity_error_handler

pytestmark = pytest.mark.unit


class TestIntegrityErrorHandler:
    """Unit-тесты для integrity_error_handler."""

    async def test_returns_409_response(self) -> None:
        """Проверка, что обработчик возвращает 409 Conflict."""
        request = MagicMock(spec=Request)
        exc = IntegrityError("INSERT INTO ...", params={}, orig=Exception("Duplicate key"))

        response = await integrity_error_handler(request, exc)

        assert response.status_code == status.HTTP_409_CONFLICT  # noqa: S101
        assert response.body is not None  # noqa: S101

    async def test_response_contains_detail(self) -> None:
        """Проверка, что ответ содержит детали ошибки."""
        request = MagicMock(spec=Request)
        exc = IntegrityError("INSERT INTO ...", params={}, orig=Exception("Duplicate key"))

        response = await integrity_error_handler(request, exc)

        import json

        assert isinstance(response.body, str | bytes)  # noqa: S101
        body = json.loads(response.body)
        assert "detail" in body  # noqa: S101
