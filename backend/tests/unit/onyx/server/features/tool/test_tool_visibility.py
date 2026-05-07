from types import SimpleNamespace

from onyx.server.features.tool.tool_visibility import is_agent_creation_selectable
from onyx.server.features.tool.tool_visibility import is_chat_selectable
from onyx.server.features.tool.tool_visibility import should_expose_tool_to_fe


def test_python_tool_is_hidden_from_frontend() -> None:
    tool = SimpleNamespace(in_code_tool_id="PythonTool")

    assert should_expose_tool_to_fe(tool) is False
    assert is_chat_selectable(tool) is False
    assert is_agent_creation_selectable(tool) is False
