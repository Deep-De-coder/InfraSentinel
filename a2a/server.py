from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from packages.agents.cmdb_validator import CMDBValidatorAgent
from packages.agents.mop_compliance import MOPComplianceAgent
from packages.agents.vision_verifier import VisionVerifierAgent
from packages.core.models import CVCableTagResult, CVPortLabelResult, ChangeStep, ValidationResult

app = FastAPI(title="InfraSentinel A2A Placeholder")


class A2AMessage(BaseModel):
    agent: Literal["mop", "vision", "cmdb"]
    payload: dict


@app.get("/a2a/agent-card")
async def get_agent_card() -> dict:
    path = Path(__file__).with_name("agent_card.json")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/a2a/message/send")
async def send_message(msg: A2AMessage) -> dict:
    if msg.agent == "mop":
        decision = await MOPComplianceAgent().run(ChangeStep.model_validate(msg.payload))
        return decision.model_dump(mode="json")
    if msg.agent == "vision":
        port = CVPortLabelResult.model_validate(msg.payload["port"])
        cable = CVCableTagResult.model_validate(msg.payload["cable"])
        decision = await VisionVerifierAgent().run(port=port, cable=cable)
        return decision.model_dump(mode="json")
    if msg.agent == "cmdb":
        validation = ValidationResult.model_validate(msg.payload)
        decision = await CMDBValidatorAgent().run(validation=validation)
        return decision.model_dump(mode="json")
    raise HTTPException(status_code=400, detail="Unsupported agent.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090)
