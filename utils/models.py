from typing import Literal
from pydantic import BaseModel, Field


class TechBrief(BaseModel):
    summary: str = Field(
        description=(
            "1-2 sentences: what the plugin looks for and roughly how it tests for it "
            "(e.g. sends a payload and checks the response, vs. compares a version "
            "string). Plain technical English. Don't restate the plugin's name, "
            "family, CVEs, or CWEs - the tech already has those."
        )
    )
    detection_reliability: Literal["version-only", "confirmed-behavior", "unclear"] = Field(
        description=(
            "Your own read of how this plugin decides, based on the source: "
            "'version-only' if it fires on a version/banner comparison without "
            "confirming the vulnerability behaves; 'confirmed-behavior' if it sends a "
            "payload and verifies the response; 'unclear' if the source doesn't make it "
            "evident. Judge from the source itself."
        )
    )
    fp_analysis: str = Field(
        description=(
            "2-3 sentences, maximum. State the single most important false-positive "
            "risk for THIS check, if there is one, and how much confidence the tech "
            "should place in the finding. Skip hedging and don't restate facts the "
            "tech already has (paranoid-only, audit bailouts, detection reliability) - "
            "mention them only if directly relevant to the one risk you're describing. "
            "If there's no meaningful FP risk, say that in one sentence and stop."
        )
    )
