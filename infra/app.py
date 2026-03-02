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
import subprocess
import json
from stacks.propchain_stack import PropChainStack

app = cdk.App()

# Get AWS account from context or AWS CLI
account_context = app.node.try_get_context("account")
if not account_context:
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
            capture_output=True,
            text=True,
            check=True
        )
        account_context = result.stdout.strip()
    except Exception as e:
        raise RuntimeError(f"Could not determine AWS account. Ensure AWS CLI is configured: {e}")

region_context = app.node.try_get_context("region") or "ap-south-1"

PropChainStack(
    app,
    "PropChainStack",
    # CDK uses your local AWS CLI credentials by default.
    # Explicitly pin account + region so CDK never guesses wrong.
    env=cdk.Environment(
        account=account_context,
        region=region_context,
    ),
    description="PropChain — Blockchain & AI Property Platform (AI for Bharat Hackathon)",
)

app.synth()
