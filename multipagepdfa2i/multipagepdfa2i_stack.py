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
SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN_EV = ""

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

    def create_state_machine(self, services):

        task_pngextract = aws_stepfunctions_tasks.LambdaInvoke(
            self, "PDF. Conver to PNGs",
            lambda_function = services["lambda"]["pngextract"],
            payload_response_only=True,
            result_path = "$.image_keys"
        )

        task_wrapup = aws_stepfunctions_tasks.LambdaInvoke(
            self, "Wrapup and Clean",
            lambda_function = services["lambda"]["wrapup"]
        )

        iterate_sqs_to_textract = aws_stepfunctions_tasks.SqsSendMessage(
            self, "Perform Textract and A2I",
            queue=services["textract_sqs"], 
            message_body = aws_stepfunctions.TaskInput.from_object({
                "token": aws_stepfunctions.Context.task_token,
                "id.$": "$.id",
                "bucket.$": "$.bucket",
                "key.$": "$.key",
                "wip_key.$": "$.wip_key"
            }),
            delay= None,
            integration_pattern=aws_stepfunctions.ServiceIntegrationPattern.WAIT_FOR_TASK_TOKEN
        )

        process_map = aws_stepfunctions.Map(
            self, "Process_Map",
            items_path = "$.image_keys",
            result_path="DISCARD",
            parameters = {
                "id.$": "$.id",
                "bucket.$": "$.bucket",
                "key.$": "$.key",
                "wip_key.$": "$$.Map.Item.Value"
            }
        ).iterator(iterate_sqs_to_textract)
        
        choice_pass = aws_stepfunctions.Pass(
            self,
            "Image. Passing.",
            result=aws_stepfunctions.Result.from_array(["single_image"]),
            result_path="$.image_keys"
        )

        pdf_or_image_choice = aws_stepfunctions.Choice(self, "PDF or Image?")
        pdf_or_image_choice.when(aws_stepfunctions.Condition.string_equals("$.extension", "pdf"), task_pngextract)
        pdf_or_image_choice.when(aws_stepfunctions.Condition.string_equals("$.extension", "png"), choice_pass)
        pdf_or_image_choice.when(aws_stepfunctions.Condition.string_equals("$.extension", "jpg"), choice_pass)

        # Creates the Step Functions
        multipagepdfa2i_sf = aws_stepfunctions.StateMachine(
            scope = self, 
            id = "multipagepdfa2i_stepfunction",
            state_machine_name = "multipagepdfa2i_stepfunction",
            definition=pdf_or_image_choice.afterwards().next(process_map).next(task_wrapup)
        )

        return multipagepdfa2i_sf

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
                    's3:PutObject',
                    'lambda:InvokeFunction',
                    'states:StartExecution',
                    'sts:AssumeRole',
                    'sqs:DeleteMessage',
                    'sqs:ReceiveMessage',
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
                    'sts:AssumeRole',
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ]
            )
        )

        return lam_roles

    def create_lambda_functions(self, services):
        lambda_functions = {}
        
        lambda_functions["pngextract"] = aws_lambda.Function(
            scope=self,
            id="multipagepdfa2i_pngextract",
            function_name="multipagepdfa2i_pngextract",
            code=aws_lambda.Code.from_asset("./deploy_code/multipagepdfa2i_pngextract/multipagepdfa2i_pngextract.jar"),
            handler="Lambda::handleRequest",
            runtime=aws_lambda.Runtime.JAVA_11,
            timeout=core.Duration.minutes(15),
            memory_size=3000,
            role=services["lam_roles"]["pngextract"]
        )

        lambda_functions["analyzepdf"] = aws_lambda.Function(
                scope=self,
                id="multipagepdfa2i_analyzepdf",
                function_name="multipagepdfa2i_analyzepdf",
                code=aws_lambda.Code.from_asset("./deploy_code/multipagepdfa2i_analyzepdf/"),
                handler="lambda_function.lambda_handler",
                runtime=aws_lambda.Runtime.PYTHON_3_8,
                timeout=core.Duration.minutes(3),
                memory_size=3000,
                role=services["lam_roles"]["analyzepdf"],
                environment= {
                    "sqs_url": services["textract_sqs"].queue_url,
                    "human_workflow_arn": SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN_EV
                }
        )

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
                role=services["lam_roles"][name]
            )

        return lambda_functions

    def create_events(self, services):
        # kickoff_notification = aws_s3_notifications.LambdaDestination(services["lambda"]["kickoff"])
        extensions = [
            "pdf", "pDf", "pDF", "pdF", "PDF", "Pdf",
            "png", "pNg", "pNG", "pnG", "PNG", "Png",
            "jpg", "jPg", "jPG", "jpG", "JPG", "Jpg"
        ]
        for extension in extensions:
            services["main_s3_bucket"].add_event_notification(
                aws_s3.EventType.OBJECT_CREATED,  
                aws_s3_notifications.SqsDestination(services["sf_sqs"]),
                aws_s3.NotificationKeyFilter(prefix="uploads/", suffix=extension)
            )    
        
        services["lambda"]["kickoff"].add_event_source(
            aws_lambda_event_sources.SqsEventSource(
                services["sf_sqs"], 
                batch_size=1
            )
        )
        
        services["lambda"]["analyzepdf"].add_event_source(
            aws_lambda_event_sources.SqsEventSource(
                services["textract_sqs"], 
                batch_size=1
            )
        )

        human_complete_target = aws_events_targets.LambdaFunction(services["lambda"]["humancomplete"])

        human_review_event_pattern = aws_events.EventPattern(
            source=["aws.sagemaker"],
            detail_type=["SageMaker A2I HumanLoop Status Change"]
        )

        aws_events.Rule(self, 
            "multipadepdfa2i_HumanReviewComplete", 
            event_pattern=human_review_event_pattern,
            targets=[human_complete_target]
        )

    def create_services(self):
        services = {}
        # S3 bucket
        services["main_s3_bucket"] = aws_s3.Bucket(self, "multipagepdfa2i", removal_policy=core.RemovalPolicy.DESTROY)
        self.configure_dynamo_table("multia2ipdf_callback", "jobid", "callback_token")

        services["sf_sqs"] = aws_sqs.Queue(
            self, "multipagepdfa2i_sf_sqs",
            queue_name = "multipagepdfa2i_sf_sqs",
            visibility_timeout=core.Duration.minutes(5)
        )

        services["textract_sqs"] = aws_sqs.Queue(
            self, "multipagepdfa2i_textract_sqs",
            queue_name = "multipagepdfa2i_textract_sqs",
            visibility_timeout=core.Duration.minutes(3)
        )
        

        services["lam_roles"] = self.create_iam_role_for_lambdas()
        services["lambda"] = self.create_lambda_functions(services)

        services["sf"] = self.create_state_machine(services)

        # need to creak kick off here so we can pass the state machine arn...
        services["lambda"]["kickoff"] = aws_lambda.Function(
                scope=self,
                id="multipagepdfa2i_kickoff",
                function_name="multipagepdfa2i_kickoff",
                code=aws_lambda.Code.from_asset("./deploy_code/multipagepdfa2i_kickoff/"),
                handler="lambda_function.lambda_handler",
                runtime=aws_lambda.Runtime.PYTHON_3_8,
                timeout=core.Duration.minutes(5),
                memory_size=3000,
                role=services["lam_roles"]["kickoff"],
                environment= {
                    "sqs_url": services["sf_sqs"].queue_url,
                    "state_machine_arn": services["sf"].state_machine_arn
                }
        )

        return services


    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        services = self.create_services()
        self.create_events(services)

        