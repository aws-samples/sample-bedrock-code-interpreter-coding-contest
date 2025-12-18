import base64
import boto3

ssm = boto3.client('ssm', region_name='us-east-1')

def handler(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    uri = request['uri']
    
    # Only require auth for admin.html
    if uri != '/admin.html' and not uri.endswith('/admin.html'):
        return request
    
    username = ssm.get_parameter(Name='/coding-contest/admin-username')['Parameter']['Value']
    password = ssm.get_parameter(Name='/coding-contest/admin-password')['Parameter']['Value']
    
    auth_string = f'{username}:{password}'
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    required_auth = f'Basic {encoded_auth}'
    
    if 'authorization' in headers:
        if headers['authorization'][0]['value'] == required_auth:
            return request
    
    return {
        'status': '401',
        'statusDescription': 'Unauthorized',
        'headers': {
            'www-authenticate': [{'key': 'WWW-Authenticate', 'value': 'Basic realm="Admin Area"'}]
        }
    }
