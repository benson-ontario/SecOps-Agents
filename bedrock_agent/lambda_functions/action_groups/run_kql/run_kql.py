"""fetches selected queries from s3 bucket and executes them.
Acts as client for azure mcp server (on EC2 Eliz_ubuntu) and belongs to the executeQueries action group.
"""
import logging
from http import HTTPStatus
import asyncio, aiohttp
import os
import boto3
from typing import Any, Dict
import re
import json


logger = logging.getLogger()
logger.setLevel(logging.INFO)
print("Current dir:", os.listdir(os.path.dirname(__file__))) # to ensure that current directory has query packs.
# config
MCP_BASE_URL = os.environ['MCP_BASE_URL']
WORKSPACE = os.environ['WORKSPACE']
TENANT_ID = os.environ['TENANT_ID']
TABLE = os.environ['TABLE']
SUBSCRIPTION = os.environ['SUBSCRIPTION']
RESOURCE_GROUP = os.environ['RESOURCE_GROUP']
COMMAND = os.environ['COMMAND']
INTENT = os.environ['INTENT']
PACKS_S3_BUCKET = os.environ['PACKS_S3_BUCKET']
PACKS_S3_PREFIX = os.environ['PACKS_S3_PREFIX']

s3 = boto3.client('s3')
bucket = s3.get_object(Bucket=PACKS_S3_BUCKET, Key=PACKS_S3_PREFIX)


def load_json():
    filepath = os.path.join(os.path.dirname(__file__), 'queries.json')
    try:
        with open(filepath) as f:
            data = json.load(f)
    except Exception as e:
        print('JSON loading error: ', e)
    return data


def preprocess_params(parameters, action_group, apiPath, httpMethod):
    param_map = {param['name']: param['value'].strip()[1:-1] for param in parameters} # dict for lookup. [1:-1] deletes '{}' and '[]' marks

    query_ids = [query.strip() for query in param_map['queries'].split(',')]
    # preprocess substitutions
    substitutions = dict(
        sub.strip().split('=', 1)
        for sub in param_map['substitutions'].strip("'{}").split(',')
        if '=' in sub
    )
    # data = json.loads(bucket['Body'].read())
    descriptions = load_json()
    #print(data)
    descriptions = {desc['QueryID']: desc for desc in descriptions['Queries']} # dict for query lookup

    tool_name = apiPath.strip('/')
    query_to_be = [] # query list for tasks
    print(query_ids)
    print(substitutions)

    for id in query_ids:
        # get query
        if id not in descriptions:
            print(f'Query {id} was not found.')
            continue

        try:
            query_data = descriptions[id]
            subs_key = query_data.get('Subs')
            if subs_key:
                subst_value = substitutions.get(subs_key)
                query = query_data['Query'].format(**{subs_key: subst_value})
            else:
                query = query_data['Query']
            table_name = re.search(r'^(?!let\b)(\w+)', query, re.MULTILINE).group(1) # look for a table name, skips 'let'
            funct_args = {
                'command': COMMAND,
                'intent': INTENT,
                'parameters': {
                    'table': table_name,
                    'query': query,
                    "workspace": WORKSPACE,
                    "tenant": TENANT_ID,
                    "subscription": SUBSCRIPTION,
                    "resource-group": RESOURCE_GROUP
                }
            }

            query_to_be.append({'tool': tool_name, 'function_args': funct_args})
        
        except Exception as e:
            print('error happened for ', query, 'eror:', e)

    return query_to_be


async def post_tool(params_set):
    try:
        results = {'results': []} # final log results
        async with aiohttp.ClientSession() as session:
            tasks = [
                session.post(
                MCP_BASE_URL,
                json={'tool': q['tool'], 'function_args': q['function_args']},
                timeout=aiohttp.ClientTimeout(total=90)) for q in params_set
            ]
            responses = await asyncio.gather(*tasks) 
            for response, q in zip(responses, params_set):
                data = await response.json()
                data_result = {
                    "query_executed": q['function_args']['parameters']['query'],
                    "table": q['function_args']['parameters']['table'],
                    "logs": data
                }
                results['results'].append(data_result)
            return results

    except aiohttp.ClientResponseError as e:
        print(f"HTTP error occurred: {e.status}, message: {e.message}")
    except aiohttp.ClientConnectionError as e:
        print(f"Connection error occurred: {e}")
    except aiohttp.ClientError as e:
        print(f"An aiohttp client error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        parameters = event['requestBody']['content']['application/json']['properties']
        action_group = event['actionGroup']
        apiPath = event['apiPath']
        httpMethod = event['httpMethod']
        message_version = event.get('messageVersion', '1.0')
        # utils call
        print('EVENT')
        print(event)
        params = preprocess_params(parameters, action_group, apiPath, httpMethod)
        results = asyncio.run(post_tool(params))

        response_body = {'application/json': {'body': results}}
        action_response = {
            'actionGroup': action_group,
            'apiPath': apiPath,
            'httpMethod': httpMethod,
            'httpStatusCode': 200,
            'responseBody': response_body
        }
        final_message = {
            'response': action_response,
            'messageVersion': message_version
        }

        logger.info('Response: %s', final_message)
        return final_message

    except KeyError as e:
        logger.error('Missing required field: %s', str(e))
        return {
            'statusCode': HTTPStatus.BAD_REQUEST,
            'body': f'Error: missing field {str(e)}'
        }

    except Exception as e:
        logger.error('Handler error: %s', str(e))
        return {
            'statusCode': HTTPStatus.INTERNAL_SERVER_ERROR,
            'body': f'Error: {str(e)}'
        }