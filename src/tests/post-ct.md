CTManager: 016065782247
CTAudit: 746869318262
CTLog: 211875017857
CTApp1: 119399605612

SSO: https://d-976709ad96.awsapps.com/start 
craigar@


# CTManager Admin

## Enable trusted access for CloudFormation StackSets via CloudFormation console
> https://ap-southeast-2.console.aws.amazon.com/cloudformation/home?region=ap-southeast-2#/stacksets


> <https://aws.amazon.com/premiumsupport/knowledge-center/config-organizations-admin/>

`aws organizations list-aws-service-access-for-organization`

```json
{
    "EnabledServicePrincipals": [
        {
            "ServicePrincipal": "config.amazonaws.com",
            "DateEnabled": "2021-09-30T10:53:15.536000+13:00"
        },
        {
            "ServicePrincipal": "controltower.amazonaws.com",
            "DateEnabled": "2021-09-23T11:35:58.966000+12:00"
        },
        {
            "ServicePrincipal": "member.org.stacksets.cloudformation.amazonaws.com",
            "DateEnabled": "2021-10-12T20:19:35.280000+13:00"
        },
        {
            "ServicePrincipal": "sso.amazonaws.com",
            "DateEnabled": "2021-09-23T11:36:37.392000+12:00"
        }
    ]
}
```

`aws organizations enable-aws-service-access --service-principal=config-multiaccountsetup.amazonaws.com`

`aws organizations register-delegated-administrator --service-principal config.amazonaws.com --account-id` **CTAudit**

`aws organizations register-delegated-administrator --service-principal config-multiaccountsetup.amazonaws.com --account-id` **CTAudit**

`aws organizations register-delegated-administrator --service-principal member.org.stacksets.cloudformation.amazonaws.com --account-id` **CTAudit**


`aws organizations list-aws-service-access-for-organization`
```json
{
    "EnabledServicePrincipals": [
        {
            "ServicePrincipal": "config-multiaccountsetup.amazonaws.com",
            "DateEnabled": "2021-10-05T10:40:06.402000+13:00"
        },
        {
            "ServicePrincipal": "config.amazonaws.com",
            "DateEnabled": "2021-09-30T10:53:15.536000+13:00"
        },
        {
            "ServicePrincipal": "controltower.amazonaws.com",
            "DateEnabled": "2021-09-23T11:35:58.966000+12:00"
        },
        {
            "ServicePrincipal": "member.org.stacksets.cloudformation.amazonaws.com",
            "DateEnabled": "2021-10-12T20:19:35.280000+13:00"
        },
        {
            "ServicePrincipal": "sso.amazonaws.com",
            "DateEnabled": "2021-09-23T11:36:37.392000+12:00"
        }
    ]
}
```

`aws organizations list-delegated-administrators --service-principal=config.amazonaws.com`          
```json
{
    "DelegatedAdministrators": [
        {
            "Id": "746869318262",
            "Arn": "arn:aws:organizations::016065782247:account/o-fq05wy5k0j/746869318262",
            "Email": "craigar+ctaudit@amazon.com",
            "Name": "Audit",
            "Status": "ACTIVE",
            "JoinedMethod": "CREATED",
            "JoinedTimestamp": "2021-09-23T11:36:16.074000+12:00",
            "DelegationEnabledDate": "2021-10-03T17:47:22.634000+13:00"
        }
    ]
}
```

`aws organizations list-delegated-administrators --service-principal=config-multiaccountsetup.amazonaws.com`
```json
{
    "DelegatedAdministrators": [
        {
            "Id": "746869318262",
            "Arn": "arn:aws:organizations::016065782247:account/o-fq05wy5k0j/746869318262",
            "Email": "craigar+ctaudit@amazon.com",
            "Name": "Audit",
            "Status": "ACTIVE",
            "JoinedMethod": "CREATED",
            "JoinedTimestamp": "2021-09-23T11:36:16.074000+12:00",
            "DelegationEnabledDate": "2021-10-05T10:41:07.792000+13:00"
        }
    ]
}
```

`aws organizations list-delegated-administrators --service-principal=member.org.stacksets.cloudformation.amazonaws.com`
```json
{
    "DelegatedAdministrators": [
        {
            "Id": "746869318262",
            "Arn": "arn:aws:organizations::016065782247:account/o-fq05wy5k0j/746869318262",
            "Email": "craigar+ctaudit@amazon.com",
            "Name": "Audit",
            "Status": "ACTIVE",
            "JoinedMethod": "CREATED",
            "JoinedTimestamp": "2021-09-23T11:36:16.074000+12:00",
            "DelegationEnabledDate": "2021-10-12T20:23:30.476000+13:00"
        }
    ]
}
```

# CTAudit Admin

> Download 
https://raw.githubusercontent.com/awslabs/aws-config-rules/master/aws-config-conformance-packs/Operational-Best-Practices-for-NZISM.yaml > 

`aws configservice put-organization-conformance-pack --organization-conformance-pack-name NZISM --template-body file://operational-best-practices-for-nzism.yaml
```json
{
    "OrganizationConformancePackArn": "arn:aws:config:ap-southeast-2:016065782247:organization-conformance-pack/NZISM-ra3floco"
}
```

## Create Aggregator via Console
* Select source accounts: `Add my organization`
* Choose a role: `aws-controltower-ConfigRecorderRole`
* Regions: `ap-southeast-2`


# CTApp1

## Automatically provisioned
`arn:aws:iam::119399605612:role/aws-controltower-AdministratorExecutionRole`
Permissions=AdministratorAccess
Trust
```json
{
"Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::746869318262:role/aws-controltower-AuditAdministratorRole"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
where
`arn:aws:iam::746869318262:role/aws-controltower-AuditAdministratorRole`
can be assumed by lambda and has
AWSLambdaExecute and
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "sts:AssumeRole"
            ],
            "Resource": [
                "arn:aws:iam::*:role/aws-controltower-AdministratorExecutionRole"
            ],
            "Effect": "Allow"
        }
    ]
}
```

#ALZ
`arn:aws:iam::344889197339:role/AWSLandingZoneAdminExecutionRole`
Permissions=AdministratorAccess
```json
{
"Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::469231310320:role/AWSLandingZoneSecurityAdministratorRole"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
where
344889197339 = application account
469231310320 = security account