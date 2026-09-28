import boto3
import io
import zipfile


sts = boto3.client("sts")

account = sts.get_caller_identity()["Account"]

role_arn = f"arn:aws:iam::{account}:role/LabRole"

print("Account:", account)
print("Role ARN:", role_arn)
lambda_client = boto3.client("lambda")

print("Lambda client créé")
lambda_code = """
def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "body": "Hello from Lambda!"
    }
"""

package_buffer = io.BytesIO()

with zipfile.ZipFile(package_buffer, "w") as z:
    z.writestr("lambda_function.py", lambda_code)

package_bytes = package_buffer.getvalue()

print("Package Lambda créé")
name = "ma-premiere-lambda"

response = lambda_client.create_function(
    FunctionName=name,
    Runtime="python3.13",
    Role=role_arn,
    Handler="lambda_function.lambda_handler",
    Code={"ZipFile": package_bytes},
)

print("Lambda créée :", response["FunctionArn"])