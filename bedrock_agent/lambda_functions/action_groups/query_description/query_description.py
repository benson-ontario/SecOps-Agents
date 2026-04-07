import os
import logging
from typing import Dict, Any
from http import HTTPStatus

logger = logging.getLogger()
logger.setLevel(logging.INFO)


PACK_FILES = {
    'user': 'QueriesMD/USER_INVESTIGATION_V1.md',
    'ip': 'QueriesMD/IP_INVESTIGATION_V1.md',
}


def load_pack(entity):
    filename = PACK_FILES.get(entity.lower())
    if not filename:
        raise ValueError(f"No pack found for entity type: {entity}")

    file_path = os.path.join(os.path.dirname(__file__), filename)
    with open(file_path, 'r') as f:
        return f.read()


def get_queries(entities):
    packs = []
    entities = entities.split(',')
    for entity in entities:
        try:
            print("FILE")
            print(entity.strip())
            file = load_pack(entity.strip())
            packs.append(file)
        except ValueError as e:
            return [f"Error occurred: {str(e)}"]
    return packs


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
    print(event)
    try:
        action_group = event['actionGroup']
        function = event['function']
        message_version = event.get('messageVersion',1)
        parameters = event.get('parameters', [])
        entities = parameters[0].get('value')
        queries = get_queries(entities)
        # Execute your business logic here. For more information, 
        # refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
        response_body = {
            'TEXT': {
                'body': '\n\n---\n\n'.join(queries)
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
        logger.error('Unexpected error: %s', str(e))
        return {
            'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
            'body': 'Internal server error'
        }
