import json
import os
import requests
import uuid
import datetime
import boto3

BEDROCK_AGENT_ID = os.environ['BEDROCK_AGENT_ID']
BEDROCK_AGENT_ALIAS_ID = os.environ['BEDROCK_AGENT_ALIAS_ID']

bedrock = boto3.client('bedrock-agent-runtime')


def invoke_bedrock_agent(session, payload):
    response = bedrock.invoke_agent(
        agentId=BEDROCK_AGENT_ID,
        agentAliasId=BEDROCK_AGENT_ALIAS_ID,
        sessionId=session,
        inputText=payload,
        enableTrace=True
    )

    output = ""
    for event in response["completion"]:
        if "chunk" in event:
            output += event["chunk"]["bytes"].decode("utf-8")

    return output


def lambda_handler(event, context):
    prompt = event.get('body')
    session = str(uuid.uuid4())
    print('Event')
    print(event)
    agent_message = invoke_bedrock_agent(session, prompt)
    # score = get_confidence_score(agent_message)
    print('AGENT RESPONSE')
    print(agent_message)
    
    agent_response = {"message": agent_message}
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "body": json.dumps(agent_response),
        "headers": {
            "Content-Type": "application/json"
        }
    }
