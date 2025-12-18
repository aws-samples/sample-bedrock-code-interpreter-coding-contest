import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['GAME_STATE_TABLE'])

def handler(event, context):
    try:
        http_method = event['httpMethod']
        
        if http_method == 'GET':
            # ゲーム状態を取得
            response = table.get_item(Key={'state_key': 'game_active'})
            is_active = response.get('Item', {}).get('value', False)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'is_active': is_active})
            }
        
        elif http_method == 'POST':
            # ゲーム状態を更新
            body = json.loads(event['body'])
            is_active = body.get('is_active', True)
            
            table.put_item(Item={
                'state_key': 'game_active',
                'value': is_active
            })
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'message': 'Game state updated', 'is_active': is_active})
            }
        
        else:
            return {
                'statusCode': 405,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Method not allowed'})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
