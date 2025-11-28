from execution_platform.router import PersonaRouter

def test_router_selects_by_capabilities():
    r = PersonaRouter()
    assert r.select_provider("code_writer") in {"claude_agent", "openai", "gemini"}

def test_router_get_client():
    r = PersonaRouter()
    client = r.get_client("code_writer")
    # Must have chat coroutine method
    assert hasattr(client, "chat")
