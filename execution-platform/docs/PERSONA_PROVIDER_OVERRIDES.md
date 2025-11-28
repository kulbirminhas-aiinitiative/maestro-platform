# Persona-level Provider Overrides

- Configure EP_PERSONA_PROVIDER_MAP_PATH to a JSON file mapping personaId -> provider.
- Example JSON:

{
  "architect": "anthropic",
  "qa_engineer": "openai",
  "local_dev": "claude_agent"
}

- Gateway uses this mapping at request-time to pick provider if caller passes personaId.
