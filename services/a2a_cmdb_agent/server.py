"""CMDB Validator Agent: observed + NetBox -> proceed/block + escalation text."""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from packages.a2a.schema import AgentCard, A2AMessage, A2AResponse
from packages.agents.cmdb import cmdb_advice
from packages.core.models.steps import StepDefinition

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    stream=sys.stderr,
)
logger = logging.getLogger("a2a_cmdb_agent")

app = FastAPI(title="CMDB Validator Agent")


@app.get("/a2a/agent-card")
async def get_agent_card() -> dict:
    card = AgentCard(
        name="CMDBValidatorAgent",
        version="0.1.0",
        capabilities=["Interpret NetBox validation", "Decide block vs proceed", "Generate escalation text"],
        endpoints={"send": "/a2a/message/send"},
    )
    return card.model_dump(mode="json")


@app.post("/a2a/message/send")
async def send_message(msg: A2AMessage) -> JSONResponse:
    logger.info("message received")
    try:
        step_def = StepDefinition.model_validate(msg.input.get("step_def", {}))
        cmdb_out = msg.input.get("cmdb_out", {})
        out = cmdb_advice(step_def, cmdb_out)
        resp = A2AResponse(
            message_id=msg.message_id,
            status="ok",
            output=out,
            notes=None,
        )
        return JSONResponse(content=resp.model_dump(mode="json"))
    except Exception as e:
        logger.exception("cmdb_advice failed")
        resp = A2AResponse(
            message_id=msg.message_id,
            status="error",
            output={},
            notes=str(e),
        )
        return JSONResponse(status_code=500, content=resp.model_dump(mode="json"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8093)
