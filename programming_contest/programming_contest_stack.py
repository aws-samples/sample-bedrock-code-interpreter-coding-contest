from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_bedrockagentcore as agentcore,
    aws_ssm as ssm,
    Duration,
    CfnOutput,
    CfnParameter,
    CustomResource,
    custom_resources as cr,
)
from constructs import Construct

class ProgrammingContestStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # CloudFormation Parameters
        admin_username_param = CfnParameter(
            self, "AdminUsername",
            type="String",
            description="Admin username for Basic Auth",
            no_echo=False,
            min_length=1,
            constraint_description="Admin username is required"
        )
        
        admin_password_param = CfnParameter(
            self, "AdminPassword",
            type="String",
            description="Admin password for Basic Auth",
            no_echo=True,
            min_length=8,
            constraint_description="Admin password must be at least 8 characters"
        )

        # DynamoDB table for leaderboard
        leaderboard_table = dynamodb.Table(
            self, "LeaderboardTable",
            partition_key=dynamodb.Attribute(name="submission_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # DynamoDB table for game state
        game_state_table = dynamodb.Table(
            self, "GameStateTable",
            partition_key=dynamodb.Attribute(name="state_key", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # Initialize game state to false
        init_lambda = _lambda.SingletonFunction(
            self, "InitGameState",
            uuid="init-game-state",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_inline("""
import boto3
import json

def handler(event, context):
    if event['RequestType'] == 'Create':
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(event['ResourceProperties']['TableName'])
        table.put_item(Item={'state_key': 'game_active', 'value': False})
    return {'PhysicalResourceId': 'game-state-init'}
"""),
            timeout=Duration.seconds(10)
        )
        game_state_table.grant_write_data(init_lambda)
        
        CustomResource(
            self, "InitGameStateResource",
            service_token=cr.Provider(self, "InitProvider", on_event_handler=init_lambda).service_token,
            properties={"TableName": game_state_table.table_name}
        )

        # Code Interpreter for secure sandbox execution
        code_interpreter = agentcore.CfnCodeInterpreterCustom(
            self, "CodeInterpreter",
            name="contest_interpreter",
            network_configuration=agentcore.CfnCodeInterpreterCustom.CodeInterpreterNetworkConfigurationProperty(
                network_mode="SANDBOX"
            )
        )

        # S3 bucket for website hosting (private)
        website_bucket = s3.Bucket(
            self, "WebsiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )

        # Lambda function for code submission
        submit_lambda = _lambda.Function(
            self, "SubmitFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="submit.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            environment={
                "LEADERBOARD_TABLE": leaderboard_table.table_name,
                "GAME_STATE_TABLE": game_state_table.table_name,
                "CODE_INTERPRETER_ID": code_interpreter.attr_code_interpreter_id,
                "WEBSITE_BUCKET": website_bucket.bucket_name
            }
        )
        
        # Grant Code Interpreter permissions to Lambda
        submit_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock-agentcore:StartCodeInterpreterSession",
                "bedrock-agentcore:InvokeCodeInterpreter",
                "bedrock-agentcore:StopCodeInterpreterSession"
            ],
            resources=[code_interpreter.attr_code_interpreter_arn]
        ))

        # Lambda function for leaderboard
        leaderboard_lambda = _lambda.Function(
            self, "LeaderboardFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="leaderboard.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(10),
            environment={
                "LEADERBOARD_TABLE": leaderboard_table.table_name
            }
        )

        # Lambda function for reset
        reset_lambda = _lambda.Function(
            self, "ResetFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="reset.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            environment={
                "LEADERBOARD_TABLE": leaderboard_table.table_name
            }
        )

        # Lambda function for game state management
        game_state_lambda = _lambda.Function(
            self, "GameStateFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="game_state.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(10),
            environment={
                "GAME_STATE_TABLE": game_state_table.table_name
            }
        )

        # Grant permissions
        leaderboard_table.grant_read_write_data(submit_lambda)
        leaderboard_table.grant_read_data(leaderboard_lambda)
        leaderboard_table.grant_read_write_data(reset_lambda)
        game_state_table.grant_read_data(submit_lambda)
        game_state_table.grant_read_write_data(game_state_lambda)
        website_bucket.grant_read(submit_lambda)

        # API Gateway
        api = apigw.RestApi(
            self, "ProgrammingContestApi",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type"]
            )
        )
        
        submit_integration = apigw.LambdaIntegration(submit_lambda)
        leaderboard_integration = apigw.LambdaIntegration(leaderboard_lambda)
        reset_integration = apigw.LambdaIntegration(reset_lambda)
        game_state_integration = apigw.LambdaIntegration(game_state_lambda)
        
        api.root.add_resource("submit").add_method("POST", submit_integration)
        api.root.add_resource("leaderboard").add_method("GET", leaderboard_integration)
        api.root.add_resource("reset").add_method("POST", reset_integration)
        
        game_state_resource = api.root.add_resource("game-state")
        game_state_resource.add_method("GET", game_state_integration)
        game_state_resource.add_method("POST", game_state_integration)

        # Lambda@Edge for Basic Auth (must be in us-east-1)
        # Store credentials in Parameter Store
        username_param = ssm.StringParameter(
            self, "AdminUsernameSSM",
            parameter_name="/coding-contest/admin-username",
            string_value=admin_username_param.value_as_string
        )
        
        password_param = ssm.StringParameter(
            self, "AdminPasswordSSM",
            parameter_name="/coding-contest/admin-password",
            string_value=admin_password_param.value_as_string,
            tier=ssm.ParameterTier.STANDARD
        )
        
        basic_auth_lambda = _lambda.Function(
            self, "BasicAuthFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="basic_auth.handler",
            code=_lambda.Code.from_asset("lambda_edge"),
            timeout=Duration.seconds(5)
        )
        
        # Grant SSM read permissions
        username_param.grant_read(basic_auth_lambda)
        password_param.grant_read(basic_auth_lambda)
        
        basic_auth_version = basic_auth_lambda.current_version

        # CloudFront distribution
        distribution = cloudfront.Distribution(
            self, "WebsiteDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(website_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                edge_lambdas=[
                    cloudfront.EdgeLambda(
                        function_version=basic_auth_version,
                        event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
                    )
                ]
            ),
            default_root_object="index.html"
        )

        # Deploy website files with API config
        config_js = f"window.API_CONFIG = {{ url: '{api.url}' }};"
        
        s3deploy.BucketDeployment(
            self, "DeployWebsite",
            sources=[
                s3deploy.Source.asset("website"),
                s3deploy.Source.asset("contents"),
                s3deploy.Source.data("config.js", config_js)
            ],
            destination_bucket=website_bucket,
            distribution=distribution,
            distribution_paths=["/*"]
        )

        # Outputs
        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "WebsiteUrl", value=f"https://{distribution.distribution_domain_name}")
