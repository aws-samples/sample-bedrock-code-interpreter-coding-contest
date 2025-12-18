import json
import boto3
import os
from decimal import Decimal
import traceback
from collections import defaultdict

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['LEADERBOARD_TABLE'])

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return int(obj)
    raise TypeError

def handler(event, context):
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        # ユーザーごとに集計
        user_data = defaultdict(lambda: {'problem1_time': None, 'problem2_time': None, 'problem3_time': None, 'problem4_time': None})
        
        for item in items:
            username = item.get('username', '')
            problem_number = int(item.get('problem_number', 0))
            timestamp = item.get('timestamp', '')
            
            if problem_number == 1:
                user_data[username]['problem1_time'] = timestamp
            elif problem_number == 2:
                user_data[username]['problem2_time'] = timestamp
            elif problem_number == 3:
                user_data[username]['problem3_time'] = timestamp
            elif problem_number == 4:
                user_data[username]['problem4_time'] = timestamp
        
        # 結果を構築
        result = []
        for username, data in user_data.items():
            # 各ユーザーの解いた問題数と最新のクリア時間を取得
            times = [data['problem1_time'], data['problem2_time'], data['problem3_time'], data['problem4_time']]
            valid_times = [t for t in times if t is not None]
            solved_count = len(valid_times)
            latest_time = max(valid_times) if valid_times else None
            
            # タイムスタンプをHH:mm:ss形式に変換
            def format_time(timestamp):
                if timestamp is None:
                    return None
                # "YYYY-MM-DD HH:MM:SS JST" から "HH:MM:SS" を抽出
                parts = timestamp.split(' ')
                if len(parts) >= 2:
                    return parts[1]
                return timestamp
            
            entry = {
                'username': username,
                'problem1_time': format_time(data['problem1_time']),
                'problem2_time': format_time(data['problem2_time']),
                'problem3_time': format_time(data['problem3_time']),
                'problem4_time': format_time(data['problem4_time']),
                'solved_count': solved_count,
                'latest_time': latest_time
            }
            result.append(entry)
        
        # 解いた問題数で降順、同じ場合は最新クリア時間で昇順ソート
        result.sort(key=lambda x: (-x['solved_count'], x['latest_time'] if x['latest_time'] else 'z'))
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, default=decimal_default)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e), 'trace': traceback.format_exc()})
        }
