"""Tests for config module."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from standup_ai.config import load_config, get_config_value


class TestLoadConfig:
    def test_returns_empty_dict_when_no_file(self, tmp_path, monkeypatch):
        fake_config = tmp_path / ".standup.yaml"
        with patch("standup_ai.config._CONFIG_PATH", fake_config):
            result = load_config()
        assert result == {}

    def test_loads_valid_yaml(self, tmp_path):
        config_file = tmp_path / ".standup.yaml"
        config_file.write_text(textwrap.dedent("""\
            style: slack
            provider: claude
            hours: 48
            paths:
              - ~/projects
              - ~/work
        """))
        with patch("standup_ai.config._CONFIG_PATH", config_file):
            result = load_config()
        assert result["style"] == "slack"
        assert result["provider"] == "claude"
        assert result["hours"] == 48
        assert result["paths"] == ["~/projects", "~/work"]

    def test_returns_empty_on_invalid_yaml(self, tmp_path):
        config_file = tmp_path / ".standup.yaml"
        config_file.write_text(": invalid: yaml: [")
        with patch("standup_ai.config._CONFIG_PATH", config_file):
            result = load_config()
        assert result == {}

    def test_returns_empty_on_non_dict_yaml(self, tmp_path):
        config_file = tmp_path / ".standup.yaml"
        config_file.write_text("- just a list\n- not a dict\n")
        with patch("standup_ai.config._CONFIG_PATH", config_file):
            result = load_config()
        assert result == {}

    def test_returns_empty_on_null_yaml(self, tmp_path):
        config_file = tmp_path / ".standup.yaml"
        config_file.write_text("")
        with patch("standup_ai.config._CONFIG_PATH", config_file):
            result = load_config()
        assert result == {}


class TestGetConfigValue:
    def test_returns_value_when_present(self):
        config = {"style": "slack", "hours": 48}
        assert get_config_value(config, "style") == "slack"
        assert get_config_value(config, "hours") == 48

    def test_returns_default_when_absent(self):
        assert get_config_value({}, "style", "standard") == "standard"
        assert get_config_value({}, "hours", 24) == 24

    def test_returns_none_default_when_not_set(self):
        assert get_config_value({}, "style") is None

    def test_does_not_mutate_config(self):
        config = {"key": "value"}
        get_config_value(config, "other", "default")
        assert "other" not in config
