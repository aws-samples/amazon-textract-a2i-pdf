# /*
#  * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  * SPDX-License-Identifier: MIT-0
#  *
#  * Permission is hereby granted, free of charge, to any person obtaining a copy of this
#  * software and associated documentation files (the "Software"), to deal in the Software
#  * without restriction, including without limitation the rights to use, copy, modify,
#  * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
#  * permit persons to whom the Software is furnished to do so.
#  *
#  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#  * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#  * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#  * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#  */

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# ~ ENTER SAGEMAKER AUGMENTED AI WORKFLOW ARN HERE:
SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN_EV = "arn:aws:sagemaker:us-east-1:645849832089:flow-definition/pdftestv2"

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

from aws_cdk import (
    core,
    aws_s3,
    aws_s3_deployment,
    aws_lambda,
    aws_iam,
    aws_s3_notifications,
    aws_dynamodb,
    aws_stepfunctions,
    aws_stepfunctions_tasks,
    aws_sqs,
    aws_lambda_event_sources,
    aws_events,
    aws_events_targets
)

class Multipagepdfa2IStack(core.Stack):

    def create_state_machine(self, lambda_functions, page_sqs):

        task_wrapup = aws_stepfunctions.Task(
            self, "task_wrapup",
            task = aws_stepfunctions_tasks.RunLambdaTask(lambda_functions["wrapup"])
        )

        tast_analyze_with_scale = aws_stepfunctions.Task(
            self, "AnalyzeWithScale",
            task=  aws_stepfunctions_tasks.SendToQueue(
                queue = page_sqs, 
                message_body = aws_stepfunctions.TaskInput.from_object(
                    {
                        "token": aws_stepfunctions.Context.task_token,
                        "id.$": "$.id",
                        "bucket.$": "$.bucket",
                        "original_upload_pdf.$": "$.original_upload_pdf",
                        "SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN.$": "$.SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN",
                        "key.$": "$.key"
                    }
                ),
                delay=None, 
                integration_pattern=aws_stepfunctions.ServiceIntegrationPattern.WAIT_FOR_TASK_TOKEN
            )
        )

        process_map = aws_stepfunctions.Map(
            self, "Process_Map",
            items_path = "$.image_keys",
            result_path="DISCARD",
            parameters = {
                "id.$": "$.id",
                "bucket.$": "$.bucket",
                "original_upload_pdf.$": "$.original_upload_pdf",
                "SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN.$": "$.SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN",
                "key.$": "$$.Map.Item.Value"
            }
        ).iterator(tast_analyze_with_scale)

        definition = process_map.next(task_wrapup)

        aws_stepfunctions.StateMachine(
            scope = self, 
            id = "multipagepdfa2i_fancy_stepfunction",
            state_machine_name = "multipagepdfa2i_fancy_stepfunction",
            definition=definition
        )

    def configure_dynamo_table(self, table_name, primary_key, sort_key):
        demo_table = aws_dynamodb.Table(
            self, table_name,
            table_name= table_name,
            partition_key=aws_dynamodb.Attribute(
                name=primary_key,
                type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name=sort_key,
                type=aws_dynamodb.AttributeType.STRING
            ),
            removal_policy=core.RemovalPolicy.DESTROY
        )


    def create_iam_role_for_lambdas(self):
        lam_roles = {}
        
        names = ["kickoff", "pngextract", "analyzepdf", "humancomplete", "wrapup"]

        for name in names:
            lam_roles[name] = aws_iam.Role(
                scope=self,
                id="multipagepdfa2i_lam_role_" + name,
                assumed_by=aws_iam.ServicePrincipal('lambda.amazonaws.com')
            )

        # !!!!kick off lambda function
        # invokes another lambda function - client.invoke
        # lists all step functions, used to look for the state machine arn - list_state_machines
        # invokes a step function - start_execution
        # puts item into dynamodb - put_item
        lam_roles["kickoff"].add_to_policy(
            statement=aws_iam.PolicyStatement(
                resources=['*'],
                actions=[
                    's3:Read',
                    'lambda:InvokeFunction',
                    'states:ListStateMachines',
                    'states:StartExecution',
                    'dynamodb:PutItem',
                    'sts:AssumeRole',
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ]
            )
        )
        #!!!! pngextract lambda function
        # s3 get object
        # s3 put object
        lam_roles["pngextract"].add_to_policy(
            statement=aws_iam.PolicyStatement(
                resources=['*'],
                actions=[
                    's3:GetObject',
                    's3:PutObject',
                    'sts:AssumeRole',
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ]
            )
        )
        # !!!! analyzepdf lambda function
        # step functions - sendtask success
        # dynmodb - put item
        # s3 put object
        # textract analyze document
        # s3 object
        # sqs delete meesage
        lam_roles["analyzepdf"].add_to_policy(
            statement=aws_iam.PolicyStatement(
                resources=['*'],
                actions=[
                    's3:Object',
                    's3:PutObject',
                    's3:GetObject',
                    'lambda:InvokeFunction',
                    'states:SendTaskSuccess',
                    'dynamodb:PutItem',
                    'textract:AnalyzeDocument',
                    'sqs:DeleteMessage',
                    'sqs:ReceiveMessage',
                    'sagemaker:StartHumanLoop',
                    'sts:AssumeRole',
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ]
            )
        )
        # !!!! humancomplete lambda function
        # step functions send task success
        # s3 put_object
        # s3 Object
        # dynamodb table query

        lam_roles["humancomplete"].add_to_policy(
            statement=aws_iam.PolicyStatement(
                resources=['*'],
                actions=[
                    's3:Object',
                    's3:PutObject',
                    's3:GetObject',
                    'states:SendTaskSuccess',
                    'dynamodb:Query',
                    'sts:AssumeRole',
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ]
            )
        )
        # !!!! wrapup lambda function
        # s3 put object
        # s3 list object v2
        # s3 delete object
        # dynamodb query
        lam_roles["wrapup"].add_to_policy(
            statement=aws_iam.PolicyStatement(
                resources=['*'],
                actions=[
                    's3:Object',
                    's3:GetObject',
                    's3:PutObject',
                    's3:DeleteObject',
                    's3:ListBucket',
                    'dynamodb:Query',
                    'sts:AssumeRole',
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ]
            )
        )

        return lam_roles

    def create_lambda_functions(self, page_sqs):
        lambda_functions = {}
        lam_roles = self.create_iam_role_for_lambdas()

        # "kickoff" lambda function
        lambda_functions["kickoff"] = aws_lambda.Function(
                scope=self,
                id="multipagepdfa2i_kickoff",
                function_name="multipagepdfa2i_kickoff",
                code=aws_lambda.Code.from_asset("./deploy_code/multipagepdfa2i_kickoff/"),
                handler="lambda_function.lambda_handler",
                runtime=aws_lambda.Runtime.PYTHON_3_8,
                timeout=core.Duration.minutes(5),
                memory_size=3000,
                role=lam_roles["kickoff"],
                environment= {"human_workflow_arn": SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN_EV}
        )
        
        # "pngextract" is special...
        lambda_functions["pngextract"] = aws_lambda.Function(
            scope=self,
            id="multipagepdfa2i_pngextract",
            function_name="multipagepdfa2i_pngextract",
            code=aws_lambda.Code.from_asset("./deploy_code/multipagepdfa2i_pngextract/multipagepdfa2i_pngextract.jar"),
            handler="DemoLambda::handleRequest",
            runtime=aws_lambda.Runtime.JAVA_11,
            timeout=core.Duration.minutes(3),
            memory_size=3000,
            role=lam_roles["pngextract"]
        )

        # "analyze" is also special as well require enviroment variable...
        lambda_functions["analyzepdf"] = aws_lambda.Function(
                scope=self,
                id="multipagepdfa2i_analyzepdf",
                function_name="multipagepdfa2i_analyzepdf",
                code=aws_lambda.Code.from_asset("./deploy_code/multipagepdfa2i_analyzepdf/"),
                handler="lambda_function.lambda_handler",
                runtime=aws_lambda.Runtime.PYTHON_3_8,
                timeout=core.Duration.minutes(3),
                memory_size=3000,
                role=lam_roles["analyzepdf"],
                environment= {"sqs_url": page_sqs.queue_url}
        )

        #create the rest
        names = [ "humancomplete", "wrapup" ]

        for name in names:
            lambda_functions[name] = aws_lambda.Function(
                scope=self,
                id="multipagepdfa2i_" + name,
                function_name="multipagepdfa2i_" + name,
                code=aws_lambda.Code.from_asset("./deploy_code/multipagepdfa2i_" + name + "/"),
                handler="lambda_function.lambda_handler",
                runtime=aws_lambda.Runtime.PYTHON_3_8,
                timeout=core.Duration.minutes(15),
                memory_size=3000,
                role=lam_roles[name]
            )

        return lambda_functions

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create Primary S3 Bucket
        main_bucket = aws_s3.Bucket(self, "multipagepdfa2i", removal_policy=core.RemovalPolicy.DESTROY)
        
        # Create sqs queue
        page_sqs = aws_sqs.Queue(
            self, "multipagepdfa2i_page_sqs",
            queue_name = "multipagepdfa2i_page_sqs",
            visibility_timeout=core.Duration.minutes(3)
        )
        
        # Create all of the Lambda Functions
        lambda_functions = self.create_lambda_functions(page_sqs)

        # Create notification that triggers kick off lambda on pdf being uploaded to kickoff
        kickoff_notification = aws_s3_notifications.LambdaDestination(lambda_functions["kickoff"])
        
        lambda_functions["analyzepdf"].add_event_source(aws_lambda_event_sources.SqsEventSource(page_sqs, batch_size=3))

        main_bucket.add_event_notification(
            aws_s3.EventType.OBJECT_CREATED,  
            kickoff_notification,
            aws_s3.NotificationKeyFilter(prefix="uploads/", suffix="pdf")
        )

        self.configure_dynamo_table("multia2ipdf_callback", "jobid", "callback_token")
        self.configure_dynamo_table("multipagepdfa2i_upload_ids", "id", "key")       

        self.create_state_machine(lambda_functions, page_sqs)

        human_complete_target = aws_events_targets.LambdaFunction(lambda_functions["humancomplete"])

        human_review_event_pattern = aws_events.EventPattern(
            source=["aws.sagemaker"],
            detail_type=["SageMaker A2I HumanLoop Status Change"]
        )

        aws_events.Rule(self, 
            "multipadepdfa2i_HumanReviewComplete", 
            event_pattern=human_review_event_pattern,
            targets=[human_complete_target]
        )

        