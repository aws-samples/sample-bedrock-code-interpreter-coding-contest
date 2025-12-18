import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['LEADERBOARD_TABLE'])

def handler(event, context):
    try:
        # テーブルの全アイテムを削除
        response = table.scan()
        
        with table.batch_writer() as batch:
            for item in response['Items']:
                batch.delete_item(Key={'submission_id': item['submission_id']})
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'message': 'Leaderboard reset successfully'})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
