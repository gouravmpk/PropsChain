#!/usr/bin/env python3
"""
PropChain CDK App — entry point.

Usage:
    cd infra
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cdk bootstrap          # one-time per AWS account/region
    cdk deploy             # deploy everything
    cdk diff               # preview changes before deploying
    cdk destroy            # tear everything down (careful!)
"""
import aws_cdk as cdk
from stacks.propchain_stack import PropChainStack

app = cdk.App()

PropChainStack(
    app,
    "PropChainStack",
    # CDK uses your local AWS CLI credentials by default.
    # Explicitly pin account + region so CDK never guesses wrong.
    env=cdk.Environment(
        account=app.node.try_get_context("account"),   # pass via: cdk deploy -c account=123456789
        region=app.node.try_get_context("region") or "ap-south-1",
    ),
    description="PropChain — Blockchain & AI Property Platform (AI for Bharat Hackathon)",
)

app.synth()
