import json
import boto3
import os
import uuid
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource('dynamodb')
bedrock_agentcore = boto3.client('bedrock-agentcore')
s3 = boto3.client('s3')
table = dynamodb.Table(os.environ['LEADERBOARD_TABLE'])
game_state_table = dynamodb.Table(os.environ['GAME_STATE_TABLE'])
code_interpreter_id = os.environ['CODE_INTERPRETER_ID']
bucket_name = os.environ['WEBSITE_BUCKET']

response = s3.get_object(Bucket=bucket_name, Key='problems.json')
PROBLEMS = {int(k): {'test_cases': [tuple(tc) for tc in v['test_cases']]} for k, v in json.loads(response['Body'].read()).items()}

def execute_all_tests(code, test_cases):
    try:
        code = code.replace('\\n', '\n').replace('\\t', '\t')
        session = bedrock_agentcore.start_code_interpreter_session(
            codeInterpreterIdentifier=code_interpreter_id,
            name='solver-session',
            sessionTimeoutSeconds=60
        )
        session_id = session['sessionId']
        
        try:
            bedrock_agentcore.invoke_code_interpreter(
                codeInterpreterIdentifier=code_interpreter_id,
                sessionId=session_id,
                name='writeFiles',
                arguments={'content': [{'path': 'solver.py', 'text': code}]}
            )
            
            results = []
            for test_input in test_cases:
                exec_code = f"from solver import solver\nprint(solver({repr(test_input)}))" if test_input is not None else "from solver import solver\nprint(solver())"
                
                response = bedrock_agentcore.invoke_code_interpreter(
                    codeInterpreterIdentifier=code_interpreter_id,
                    sessionId=session_id,
                    name='executeCode',
                    arguments={'language': 'python', 'code': exec_code}
                )
                
                output = ''
                for event in response['stream']:
                    if 'result' in event and 'content' in event['result']:
                        for content in event['result']['content']:
                            if content['type'] == 'text':
                                output += content['text']
                
                results.append(output.strip())
            
            return results, None
        finally:
            bedrock_agentcore.stop_code_interpreter_session(
                codeInterpreterIdentifier=code_interpreter_id,
                sessionId=session_id
            )
    except Exception as e:
        return None, f"Execution error: {str(e)}"

def check_problem(problem_number, code):
    if problem_number not in PROBLEMS:
        return False
    
    test_cases = PROBLEMS[problem_number]['test_cases']
    inputs = [tc[0] for tc in test_cases]
    expected = [tc[1] for tc in test_cases]
    
    code = code.replace('\\n', '\n').replace('\\t', '\t')
    results, error = execute_all_tests(code, inputs)
    
    return not error and results == expected


def handler(event, context):
    try:
        game_state_response = game_state_table.get_item(Key={'state_key': 'game_active'})
        is_active = game_state_response.get('Item', {}).get('value', False)
        
        if not is_active:
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Game is not active. Submissions are currently disabled.'})
            }
        
        body = json.loads(event['body'])
        username = body['username']
        problem_number = body['problem_number']
        code = body['code']
        
        if problem_number not in PROBLEMS:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': f'Problem {problem_number} does not exist.'})
            }
        
        jst = timezone(timedelta(hours=9))
        timestamp = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S JST')
        
        is_correct = check_problem(problem_number, code)
        
        if is_correct:
            # 既存の記録を確認
            response = table.scan(
                FilterExpression='username = :u AND problem_number = :p',
                ExpressionAttributeValues={':u': username, ':p': problem_number}
            )
            
            if response['Items']:
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'result': 'correct',
                        'message': 'Already solved. No update to leaderboard.'
                    })
                }
            
            submission_id = str(uuid.uuid4())
            
            table.put_item(
                Item={
                    'submission_id': submission_id,
                    'username': username,
                    'problem_number': problem_number,
                    'timestamp': timestamp
                }
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'result': 'correct',
                    'message': 'Congratulations! Added to leaderboard.',
                    'submission_id': submission_id
                })
            }
        else:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'result': 'incorrect',
                    'message': 'Code is incorrect. Try again.'
                })
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
