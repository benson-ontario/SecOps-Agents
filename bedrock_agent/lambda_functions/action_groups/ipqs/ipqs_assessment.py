
import os
import json
import requests
import logging
from typing import Dict, Any
from http import HTTPStatus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = requests.Session()

IPQS_API_KEY = os.environ['IPQS_API_KEY']

def investigate_ip(ip_address):
    url = f'https://www.ipqualityscore.com/api/json/ip/{IPQS_API_KEY}/{ip_address}'
    params = {
        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'strictness': 0,
        'allow_public_access_points': 'true'
    }
    response = session.get(url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for processing Bedrock agent requests.
    
    Args:
        event (Dict[str, Any]): The Lambda event containing action details
        context (Any): The Lambda context object
    
    Returns:
        Dict[str, Any]: Response containing the action execution results
    
    Raises:
        KeyError: If required fields are missing from the event
    """
    try:
        action_group = event['actionGroup']
        function = event['function']
        message_version = event.get('messageVersion',1)
        parameters = event.get('parameters', [])
        ip_address = parameters[0].get('value')
        # Execute your business logic here. For more information, 
        # refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html

        ip_assessment_response = investigate_ip(ip_address)

        print("payload")
        print(ip_assessment_response)
        response_body = {
            'TEXT': {
                'body': json.dumps(ip_assessment_response)
            }
        }
        action_response = {
            'actionGroup': action_group,
            'function': function,
            'functionResponse': {
                'responseBody': response_body
            }
        }
        response = {
            'response': action_response,
            'messageVersion': message_version
        }

        logger.info('Response: %s', response)
        return response

    except KeyError as e:
        logger.error('Missing required field: %s', str(e))
        return {
            'statusCode': HTTPStatus.BAD_REQUEST,
            'body': f'Error: {str(e)}'
        }
    except Exception as e:
        return {
            "response": {
                "actionGroup": event.get("actionGroup", "unknown"),
                "function": event.get("function", "unknown"),
                "functionResponse": {
                    "responseBody": {
                        "TEXT": {
                            "body": json.dumps({
                                "error": str(e)
                            })
                        }
                    }
                }
            },
            "messageVersion": event.get("messageVersion", 1)
        }
