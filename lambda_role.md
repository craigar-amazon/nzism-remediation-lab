# arn:aws:iam::775397712397:role/NZISMRemediationLambdaRole

Trust: `lambda.amazonaws.com`

Permissions:
* AWSLambdaBasicExecutionRole
* NZISMRemediation
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups",
                "logs:AssociateKmsKey",
                "logs:PutRetentionPolicy"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "kms:DescribeKey"
            ],
            "Resource": "*"
        }
    ]
}
```