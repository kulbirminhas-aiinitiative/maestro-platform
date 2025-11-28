import anyio
from persona_gateway_client import PersonaGatewayClient

async def main():
    gw = PersonaGatewayClient()
    async for ev in gw.stream_chat("backend_developer", messages=[{"role":"user","content":"hello"}]):
        print(ev)
        if ev.get("event") == "done":
            break

if __name__ == "__main__":
    anyio.run(main)
