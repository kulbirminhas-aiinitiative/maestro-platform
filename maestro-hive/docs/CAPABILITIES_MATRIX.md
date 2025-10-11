# Provider Capabilities Matrix (v0.1)

| Capability        | Claude | OpenAI | Azure OpenAI | Vertex/Gemini | Bedrock(Claude) | Local |
|-------------------|:------:|:------:|:------------:|:-------------:|:---------------:|:-----:|
| System prompts    |   ✅    |   ✅    |      ✅       |      ⚠️       |        ✅        |  ✅   |
| Tool calling      |   ✅    |   ✅    |      ✅       |      ⚠️       |        ✅        |  ❌   |
| JSON mode         |   ✅    |   ✅    |      ✅       |      ✅       |   Model-dep     |  ⚠️   |
| Vision            |   ✅    |   ✅    |      ✅       |      ✅       |   Model-dep     |  ⚠️   |
| Streaming         |   ✅    |   ✅    |      ✅       |     gRPC      |   Model-dep     |  ⚠️   |
| Stop sequences    |   ✅    |   ✅    |      ✅       |      ⚠️       |   Model-dep     |  ⚠️   |
| Token counting    |   ✅    |   ✅    |      ✅       | chars-based   |      ✅          |  ❌   |
| Prompt caching    |   ✅    |   ✅    |      ✅       |      ❌       |      ⚠️          |  ❌   |
| Reasoning         |   ✅    |   ✅    |      ✅       |      ❌       |      ⚠️          |  ❌   |

Notes:
- Local: depends on runtime (Ollama/vLLM). Treat as Tier 3 unless proven.
- Vertex: streaming via gRPC; adapter must bridge to SSE.
