"""Celery worker configuration and placeholder task tests."""

import signal
from unittest.mock import patch

import pytest

from app.config import settings
from celery_worker import celery_app, cleanup_temp_files, process_book_task, register_temp_dir


class TestCeleryConfiguration:
    def test_broker_uses_redis(self) -> None:
        assert celery_app.conf.broker_url.startswith("redis://")

    def test_backend_uses_postgresql_by_default(self) -> None:
        backend = celery_app.conf.result_backend
        assert backend is not None
        assert backend.startswith("db+postgresql://") or backend.startswith("redis://")

    def test_settings_celery_backend_url_postgresql(self) -> None:
        if not settings.celery_result_backend:
            assert settings.celery_backend_url.startswith("db+postgresql://")

    def test_broker_connection_retry_on_startup(self) -> None:
        assert celery_app.conf.broker_connection_retry_on_startup is True

    def test_task_acks_late(self) -> None:
        assert celery_app.conf.task_acks_late is True

    def test_task_reject_on_worker_lost(self) -> None:
        assert celery_app.conf.task_reject_on_worker_lost is True

    def test_process_book_task_max_retries(self) -> None:
        assert process_book_task.max_retries == settings.celery_max_retries


class TestProcessBookTaskEager:
    def test_task_delegates_to_pipeline(self) -> None:
        with patch("celery_worker.run_process_book", return_value="livro_42_processed") as mock_run:
            celery_app.conf.task_always_eager = True
            celery_app.conf.task_eager_propagates = True
            try:
                result = process_book_task.apply(args=[42]).get()
                assert result == "livro_42_processed"
            finally:
                celery_app.conf.task_always_eager = False
                celery_app.conf.task_eager_propagates = False

        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == 42


class TestSigtermCleanup:
    def test_cleanup_temp_files_removes_registered_dirs(self, tmp_path) -> None:
        work = tmp_path / "work"
        work.mkdir()
        register_temp_dir(work)
        cleanup_temp_files()
        assert not work.exists()

    def test_sigterm_handler_calls_cleanup(self) -> None:
        from celery_worker import _handle_sigterm

        with patch("celery_worker.cleanup_temp_files") as mock_cleanup:
            _handle_sigterm(signal.SIGTERM, None)
            mock_cleanup.assert_called_once()
