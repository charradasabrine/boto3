
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key
from decimal import Decimal

TABLE_NAME = "sabrine_Students"

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def create_table():
    try:
        new_table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "student_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "student_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        print("Creating table, please wait ...")
        new_table.wait_until_exists()
        print(f"Table '{TABLE_NAME}' is ACTIVE.")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print("Table already exists.")
        else:
            raise


def show_error(error):
    """Display a readable AWS error."""
    code = error.response.get("Error", {}).get("Code", "Unknown")
    message = error.response.get("Error", {}).get("Message", str(error))
    print(f"AWS error [{code}]: {message}")





# 1. Add a student, preventing duplicates

def add_student():
    item = {
        "student_id": input("Student ID: ").strip(),
        "name": input("Full name: ").strip(),
        "email": input("Email: ").strip(),
        "program": input("Program: ").strip(),
    }

    year = input("Year (number): ").strip()
    if year.isdigit():
        item["year"] = Decimal(year)

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(student_id)",
        )
        print(f"Added student {item['student_id']}")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print("That student already exists. Use Update instead.")
        else:
            raise




def get_student():
    student_id = input("Student ID: ").strip()

    response = table.get_item(Key={"student_id": student_id})

    if "Item" not in response:
        print(f"No student with ID {student_id}")
        return

    for key, value in response["Item"].items():
        print(f"  {key:<14}: {value}")



def update_student():
    student_id = input("Student ID: ").strip()
    field = input("Field (name/email/program/year): ").strip()
    value = input("New value: ").strip()

    if field in ("year", "grade"):
        value = Decimal(value)

    try:
        response = table.update_item(
            Key={"student_id": student_id},
            UpdateExpression="SET #field = :value",
            ExpressionAttributeNames={"#field": field},
            ExpressionAttributeValues={":value": value},
            ConditionExpression="attribute_exists(student_id)",
            ReturnValues="ALL_NEW",
        )
        print("Updated:", response["Attributes"])

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print(f"No student with ID {student_id}")
        else:
            raise




def delete_student():
    student_id = input("Student ID: ").strip()

    try:
        response = table.delete_item(
            Key={"student_id": student_id},
            ConditionExpression="attribute_exists(student_id)",
            ReturnValues="ALL_OLD",
        )

        print(
            f"Deleted {response.get('Attributes', {}).get('name', student_id)}"
        )

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print(f"No student with ID {student_id}")
        else:
            raise



def list_students():
    items = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        if "LastEvaluatedKey" not in response:
            break

        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print(f"{'ID':<12} {'NAME':<24} {'PROGRAM':<24} YEAR")
    print("-" * 70)

    for item in sorted(items, key=lambda x: x["student_id"]):
        print(
            f"{item['student_id']:<12} "
            f"{item.get('name', '-'):<24} "
            f"{item.get('program', '-'):<24} "
            f"{item.get('year', '-')}"
        )

    print(f"\n{len(items)} student(s)")





def search_students():
    term = input("Program search term: ").strip()

    response = table.scan(
        FilterExpression=Attr("program").contains(term)
    )

    items = response.get("Items", [])

    if not items:
        print("No matching students found.")
        return

    for item in items:
        print(item)


def query_demo():
    student_id = input("Student ID to query: ").strip()

    response = table.query(
        KeyConditionExpression=Key("student_id").eq(student_id)
    )

    items = response.get("Items", [])

    if not items:
        print(f"No student with ID {student_id}")
        return

    for item in items:
        print(item)

def delete_table():
    answer = input(
        f"Delete table '{TABLE_NAME}' and ALL its records? (yes/no): "
    ).strip().lower()

    if answer != "yes":
        print("Table deletion cancelled.")
        return

    try:
        table.delete()
        print("Deleting table, please wait ...")
        table.wait_until_not_exists()
        print(f"Table '{TABLE_NAME}' deleted.")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print("Table does not exist.")
        else:
            raise




# Main menu
def main():
    while True:
        print("\n===================================")
        print("          STUDENT MANAGER")
        print("===================================")
        print("1. Add Student       6. Search Students")
        print("2. Get Student       7. Query demo")
        print("3. Update Student    8. Create Table")
        print("4. Delete Student    9. DELETE Table")
        print("5. List Students     0. Exit")
        print("===================================")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            add_student()
        elif choice == "2":
            get_student()
        elif choice == "3":
            update_student()
        elif choice == "4":
            delete_student()
        elif choice == "5":
            list_students()
        elif choice == "6":
            search_students()
        elif choice == "7":
            query_demo()
        elif choice == "8":
            create_table()
        elif choice == "9":
            delete_table()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Choose a number from 0 to 9.")


if __name__ == "__main__":
    main()
