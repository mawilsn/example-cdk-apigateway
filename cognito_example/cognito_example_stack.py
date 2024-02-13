from operator import index
from typing_extensions import runtime
from aws_cdk import (
    Duration,
    Stack,
    # aws_sqs as sqs,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_lambda_python_alpha as lambda_python,
    aws_lambda as _lambda,
)
from constructs import Construct

class CognitoExampleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        pool = cognito.UserPool(self, id="testpooluser")

        full_scope = cognito.ResourceServerScope(scope_name="*", 
											scope_description="Full Access")

        user_server = pool.add_resource_server("ResourceServer",
            identifier="users",
            scopes=[full_scope]
                )

        pool.add_domain(id="testDomain", cognito_domain=cognito.CognitoDomainOptions(
            domain_prefix="testdomainprefix"
        ))
        pool.add_client(id="clienttest", access_token_validity=Duration.minutes(60),
                        auth_flows=cognito.AuthFlow(custom=True, admin_user_password=True, user_srp=True),
                        generate_secret=True,
                        o_auth=cognito.OAuthSettings(scopes=[cognito.OAuthScope.resource_server(user_server, full_scope)],
                                                    flows=cognito.OAuthFlows(client_credentials=True
                                                                            )))

        auth = apigateway.CognitoUserPoolsAuthorizer(self, id="authtest", cognito_user_pools=[pool])

        lambda_basic = lambda_python.PythonFunction(self,
                                    id="testlambda",
                                    entry="lambdas/test",
                                    handler="handler",
                                    index="index.py",
                                    timeout=Duration.seconds(30),
                                    runtime=_lambda.Runtime.PYTHON_3_11
                                    )

        # api_subdomain: api-dev 
        # domainname: pearsoncloudmanagement.com

        rest_api = apigateway.RestApi(self, "test-api",
                                      rest_api_name="Test Service",
                                      description=f"Test Service",
                                      default_cors_preflight_options=apigateway.CorsOptions(
                                          allow_methods=['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT'],
                                          allow_origins=[
                                              # sam local start-api looks only for first entry so must be localhost
                                              'http://localhost:3000'
                                          ],
                                          allow_headers=['Content-Type', 'Authorization', 'X-Amz-Date', 'X-Api-Key',
                                                         'X-Amz-Security-Token', 'Api-Auth-Token'],
                                          max_age=Duration.seconds(600)),
                                      deploy_options=apigateway.StageOptions(stage_name='dev')
                                      )

        api_lambda_integration = apigateway.LambdaIntegration(handler=lambda_basic )
        lambda_api = rest_api.root.add_resource(path_part="test")

        lambda_api.add_method(http_method="POST", integration=api_lambda_integration,
                        authorizer=auth,
                        authorization_type=apigateway.AuthorizationType.COGNITO,
                        authorization_scopes=["users/*"]
                        )