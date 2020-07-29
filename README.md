# Processing PDF documents with a human loop with Amazon Textract and Amazon A2I

## Prerequisites

1. Node.js
2. Python
3. AWS Command Line Interface (AWS CLI)—for instructions, see Installing the AWS CLI)

## Deployment

The following code deploys the reference implementation in your AWS account. The solution deploys different components, including an S3 bucket, Step Functions, an Amazon Simple Queue Service (Amazon SQS) queue, and AWS Lambda functions using the AWS Cloud Development Kit (AWS CDK), which is an open-source software development framework to model and provision your cloud application resources using familiar programming languages.

1. Install AWS CDK: 
```
npm install -g aws-cdk
```
2. Download the repo to your local machine: 
```
git clone https://github.com/aws-samples/amazon-textract-a2i-pdf
```
3. Go to the folder amazon-textract-a2i-pdf and enter the following: 
```
pip install -r requirements.txt
```
4. Bootstrap AWS CDK: 
```
cdk bootstrap
```
5. Deploy: 
```
cdk deploy
```
6. Create a private team: https://docs.aws.amazon.com/sagemaker/latest/dg/sms-workforce-management.html

7. Create a human review workflow: https://console.aws.amazon.com/a2i/home?region=us-east-1#/human-review-workflows

8. Open the file multipagepdfa2i/multipagepdfa2i_stack.py. Update line 23 with the ARN of the human review workflow.

SAGEMAKER_WORKFLOW_AUGMENTED_AI_ARN_EV = ""
9. Run "cdk deploy" to update the solution with human review workflow arn.


## Clean Up
1. First you'll need to completely empty the S3 bucket that was created.
2. Finally, you'll need to run:
```
cdk destroy
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

