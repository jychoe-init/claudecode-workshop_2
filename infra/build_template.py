#!/usr/bin/env python3
"""Build a reviewable single-stack template. Does not call AWS or deploy."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    code = (ROOT / "workshop_core/api.py").read_text()
    adapter = (ROOT / "infra/lambda_handler.py").read_text().replace(
        "from workshop_core.api import ApiError, handle\n", "")
    code += "\n\n" + adapter
    compile(code, "index.py", "exec")
    sub = lambda value: {"Fn::Sub": value}
    ref = lambda value: {"Ref": value}
    attr = lambda name, key: {"Fn::GetAtt": [name, key]}
    resources = {
        "Data": {"Type": "AWS::DynamoDB::Table", "Properties": {
            "BillingMode": "PAY_PER_REQUEST", "AttributeDefinitions": [{"AttributeName": "pk", "AttributeType": "S"}],
            "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
            "TimeToLiveSpecification": {"AttributeName": "expires", "Enabled": True}}},
        "Logs": {"Type": "AWS::Logs::LogGroup", "Properties": {
            "LogGroupName": sub("/aws/lambda/${AWS::StackName}-api"), "RetentionInDays": 7}},
        "Role": {"Type": "AWS::IAM::Role", "Properties": {
            "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": [
                {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]},
            "Policies": [{"PolicyName": "workshop-api", "PolicyDocument": {
                "Version": "2012-10-17", "Statement": [
                    {"Effect": "Allow", "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
                     "Resource": attr("Data", "Arn")},
                    {"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                     "Resource": sub("arn:${AWS::Partition}:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${AWS::StackName}-api:*")}
                ]}}]}},
        "Function": {"Type": "AWS::Lambda::Function", "DependsOn": "Logs", "Properties": {
            "FunctionName": sub("${AWS::StackName}-api"), "Runtime": "python3.12", "Handler": "index.handler",
            "Role": attr("Role", "Arn"), "MemorySize": 256, "Timeout": 15,
            "Environment": {"Variables": {"TABLE_NAME": ref("Data")}}, "Code": {"ZipFile": code}}},
        "Api": {"Type": "AWS::ApiGatewayV2::Api", "Properties": {
            "Name": sub("${AWS::StackName}-api"), "ProtocolType": "HTTP"}},
        "Integration": {"Type": "AWS::ApiGatewayV2::Integration", "Properties": {
            "ApiId": ref("Api"), "IntegrationType": "AWS_PROXY", "IntegrationUri": attr("Function", "Arn"),
            "PayloadFormatVersion": "2.0", "TimeoutInMillis": 15000}},
        "Route": {"Type": "AWS::ApiGatewayV2::Route", "Properties": {
            "ApiId": ref("Api"), "RouteKey": "ANY /v1/{proxy+}",
            "Target": {"Fn::Join": ["/", ["integrations", ref("Integration")]]}}},
        "Health": {"Type": "AWS::ApiGatewayV2::Route", "Properties": {
            "ApiId": ref("Api"), "RouteKey": "GET /health",
            "Target": {"Fn::Join": ["/", ["integrations", ref("Integration")]]}}},
        "Stage": {"Type": "AWS::ApiGatewayV2::Stage", "Properties": {
            "ApiId": ref("Api"), "StageName": "$default", "AutoDeploy": True,
            "DefaultRouteSettings": {"ThrottlingBurstLimit": 100, "ThrottlingRateLimit": 50}}},
        "Invoke": {"Type": "AWS::Lambda::Permission", "Properties": {
            "FunctionName": ref("Function"), "Action": "lambda:InvokeFunction",
            "Principal": "apigateway.amazonaws.com",
            "SourceArn": sub("arn:${AWS::Partition}:execute-api:${AWS::Region}:${AWS::AccountId}:${Api}/*/*/*")}},
        "Docs": {"Type": "AWS::S3::Bucket", "Properties": {
            "PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "BlockPublicPolicy": True,
                                               "IgnorePublicAcls": True, "RestrictPublicBuckets": True}}},
        "DocsOAC": {"Type": "AWS::CloudFront::OriginAccessControl", "Properties": {
            "OriginAccessControlConfig": {"Name": sub("${AWS::StackName}-docs"),
                "OriginAccessControlOriginType": "s3", "SigningBehavior": "always", "SigningProtocol": "sigv4"}}},
        "DocsCache": {"Type": "AWS::CloudFront::CachePolicy", "Properties": {"CachePolicyConfig": {
            "Name": sub("${AWS::StackName}-docs"), "DefaultTTL": 300, "MaxTTL": 3600, "MinTTL": 0,
            "ParametersInCacheKeyAndForwardedToOrigin": {
                "EnableAcceptEncodingGzip": True, "CookiesConfig": {"CookieBehavior": "none"},
                "HeadersConfig": {"HeaderBehavior": "none"}, "QueryStringsConfig": {"QueryStringBehavior": "none"}}}}},
        "Distribution": {"Type": "AWS::CloudFront::Distribution", "Properties": {"DistributionConfig": {
            "Enabled": True, "DefaultRootObject": "index.html",
            "Origins": [{"Id": "docs", "DomainName": attr("Docs", "RegionalDomainName"),
                         "OriginAccessControlId": ref("DocsOAC"), "S3OriginConfig": {"OriginAccessIdentity": ""}}],
            "DefaultCacheBehavior": {"TargetOriginId": "docs", "ViewerProtocolPolicy": "redirect-to-https",
                                     "CachePolicyId": ref("DocsCache"), "Compress": True}}}},
        "DocsPolicy": {"Type": "AWS::S3::BucketPolicy", "Properties": {
            "Bucket": ref("Docs"), "PolicyDocument": {"Version": "2012-10-17", "Statement": [{
                "Effect": "Allow", "Principal": {"Service": "cloudfront.amazonaws.com"},
                "Action": "s3:GetObject", "Resource": sub("${Docs.Arn}/*"),
                "Condition": {"StringEquals": {"AWS:SourceArn": sub("arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${Distribution}")}}
            }]}}},
    }
    return {"AWSTemplateFormatVersion": "2010-09-09", "Description": "Ch4 fictional workflow API; no Slack integration",
            "Resources": resources, "Outputs": {
                "ApiBase": {"Value": attr("Api", "ApiEndpoint")},
                "TableName": {"Value": ref("Data")},
                "DocsBucket": {"Value": ref("Docs")},
                "DocsUrl": {"Value": {"Fn::Join": ["", ["https://", attr("Distribution", "DomainName")]]}}
            }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=".local/cloudformation.json")
    args = parser.parse_args()
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(build(), ensure_ascii=False, indent=2)
    if len(data.encode()) > 51200:
        raise ValueError("Template exceeds direct CloudFormation request limit; review packaging before deploying")
    path.write_text(data + "\n")
    print(json.dumps({"template": str(path.resolve()), "bytes": len(data.encode()), "deployed": False}))


if __name__ == "__main__":
    main()
