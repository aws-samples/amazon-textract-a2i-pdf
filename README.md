# Processing PDF documents with a human loop with Amazon Textract and Amazon A2I

## Prerequisites
Before you get started, you must install the following prerequisites:

1. Node.js
2. Python
3. AWS Command Line Interface (AWS CLI)—for instructions, see Installing the AWS CLI)

## Deployment
Deploying the solution
The following code deploys the reference implementation in your AWS account. The solution deploys different components, including an S3 bucket, Step Functions, an Amazon Simple Queue Service (Amazon SQS) queue, and AWS Lambda functions using the AWS Cloud Development Kit (AWS CDK), which is an open-source software development framework to model and provision your cloud application resources using familiar programming languages.

<!-- 0. Go into Python ENV
```
python3 -m venv .env && source .env/bin/activate
``` -->
1. Install AWS CDK: 
```
npm install -g aws-cdk
```
2. Download the PDF to your local machine: 
```
git clone https://github.com/aws-samples/amazon-textract-a2i-pdf
```
3. Go to the folder multipagepdfa2i and enter the following: 
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

