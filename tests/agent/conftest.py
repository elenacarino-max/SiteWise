"""
Fixtures compartidos de pytest para aislar logs, trazas y clientes LLM en tests/agent/.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

import sitewise.common.logging_config as logging_mod
from sitewise.agent.analyzer import SiteWiseAnalyzer
from sitewise.agent.supervisor import SiteWiseSupervisor


@pytest.fixture(autouse=True)
def aislar_trazas_y_logs(tmp_path, monkeypatch):
    """Redirige trazas y logs a tmp_path y restaura el root logger tras cada test."""
    trace_file = tmp_path / "prompts_trace.jsonl"
    log_file = tmp_path / "sitewise.log"

    monkeypatch.setenv("SITEWISE_PROMPTS_FILE", str(trace_file))
    monkeypatch.setenv("SITEWISE_LOG_FILE", str(log_file))
    monkeypatch.delenv("SITEWISE_LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    root_logger = logging.getLogger()
    prev_handlers = list(root_logger.handlers)
    prev_level = root_logger.level
    prev_configured = logging_mod._CONFIGURED

    yield {
        "tmp_path": tmp_path,
        "trace_file": trace_file,
        "log_file": log_file,
    }

    for handler in list(root_logger.handlers):
        if handler not in prev_handlers:
            handler.close()
    root_logger.handlers = prev_handlers
    root_logger.setLevel(prev_level)
    logging_mod._CONFIGURED = prev_configured


@pytest.fixture
def analyzer_simulado():
    with patch("sitewise.agent.analyzer.Groq"):
        mock_retriever = MagicMock()
        analyzer = SiteWiseAnalyzer(model_name="mock-llama", retriever=mock_retriever)
        mock_client = MagicMock()
        analyzer.client = mock_client
    return analyzer, mock_client, mock_retriever


@pytest.fixture
def supervisor_simulado():
    with patch("sitewise.agent.supervisor.Groq"):
        supervisor = SiteWiseSupervisor(model_name="mock-model")
        mock_client = MagicMock()
        supervisor.client = mock_client
    return supervisor, mock_client