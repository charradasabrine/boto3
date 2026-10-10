import sys
import boto3
from botocore.exceptions import WaiterError

ec2 = boto3.client("ec2")
ssm = boto3.client("ssm")


def list_instances():
    paginator = ec2.get_paginator("describe_instances")

    rows = []

    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                if inst["State"]["Name"] == "terminated":
                    continue

                rows.append(inst)

    if not rows:
        print("No EC2 instances found.")
        return

    for inst in rows:
        tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}

        print(
            f"{inst['InstanceId']:<21} "
            f"{inst['InstanceType']:<12} "
            f"{inst['State']['Name']:<12} "
            f"{inst.get('PublicIpAddress', '-'):<16} "
            f"{tags.get('Name', '(no name)')}"
        )
def get_latest_amazon_linux_ami():
    parameter = (
        "/aws/service/ami-amazon-linux-latest/"
        "al2023-ami-kernel-default-x86_64"
    )

    response = ssm.get_parameter(Name=parameter)

    return response["Parameter"]["Value"]



def launch_instance():
    name = input("Name tag for the instance: ").strip()

    if not name:
        print("Name cannot be empty.")
        return

    ami_id = get_latest_amazon_linux_ami()
    print(f"Using latest Amazon Linux 2023 AMI: {ami_id}")

    response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType="t3.micro",
        MinCount=1,
        MaxCount=1,
        KeyName="vockey",
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Name", "Value": name},
                {"Key": "CreatedBy", "Value": "boto3-lab"},
            ],
        }],
    )

    instance = response["Instances"][0]
    instance_id = instance["InstanceId"]

    print(
        f"Launched {instance_id}, "
        f"state = {instance['State']['Name']}"
    )

    try:
        print("Waiting for the instance to reach 'running' ...")

        waiter = ec2.get_waiter("instance_running")

        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={
                "Delay": 15,
                "MaxAttempts": 40,
            },
        )

        print("Instance is running.")

    except WaiterError:
        print("Timed out. Check the Console.")
        return

    detail = ec2.describe_instances(
        InstanceIds=[instance_id]
    )

    running = detail["Reservations"][0]["Instances"][0]

    print(
        "Public IP:",
        running.get("PublicIpAddress", "not assigned")
    )
def start_instance():
    instance_id = input("Instance ID: ").strip()

    try:
        response = ec2.start_instances(
            InstanceIds=[instance_id]
        )

        change = response["StartingInstances"][0]

        print(
            change["PreviousState"]["Name"],
            "->",
            change["CurrentState"]["Name"]
        )

        print("Waiting for the instance to reach 'running' ...")

        waiter = ec2.get_waiter("instance_running")
        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={
                "Delay": 15,
                "MaxAttempts": 40,
            }
        )

        print("Instance is running.")

    except Exception as e:
        print(f"[ERROR] {e}")
def stop_instance():
    instance_id = input("Instance ID: ").strip()

    try:
        response = ec2.stop_instances(
            InstanceIds=[instance_id]
        )

        change = response["StoppingInstances"][0]

        print(
            change["PreviousState"]["Name"],
            "->",
            change["CurrentState"]["Name"]
        )

        print("Waiting for the instance to reach 'stopped' ...")

        waiter = ec2.get_waiter("instance_stopped")
        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={
                "Delay": 15,
                "MaxAttempts": 40,
            }
        )

        print("Instance is stopped.")

    except Exception as e:
        print(f"[ERROR] {e}")


def reboot_instance():
    instance_id = input("Instance ID: ").strip()

    try:
        ec2.reboot_instances(
            InstanceIds=[instance_id]
        )

        print("Instance reboot requested.")

    except Exception as e:
        print(f"[ERROR] {e}")



def describe_instance():
    instance_id = input("Instance ID: ").strip()

    if not instance_id:
        print("Instance ID cannot be empty.")
        return

    try:
        response = ec2.describe_instances(
            InstanceIds=[instance_id]
        )

        instances = [
            inst
            for reservation in response["Reservations"]
            for inst in reservation["Instances"]
        ]

        if not instances:
            print("Instance not found.")
            return

        inst = instances[0]

        # Get the Name tag
        tags = inst.get("Tags", [])
        name = next(
            (tag["Value"] for tag in tags if tag["Key"] == "Name"),
            "(no name)"
        )

        # Print instance details
        print("\n===== EC2 INSTANCE DETAILS =====")
        print("Instance ID:", inst["InstanceId"])
        print("Name:", name)
        print("State:", inst["State"]["Name"])
        print("Instance type:", inst["InstanceType"])
        print("AMI ID:", inst["ImageId"])
        print("Availability zone:",
              inst.get("Placement", {}).get("AvailabilityZone", "N/A"))
        print("Public IP:", inst.get("PublicIpAddress", "Not assigned"))
        print("Private IP:", inst.get("PrivateIpAddress", "Not assigned"))
        print("Key pair:", inst.get("KeyName", "None"))
        print("Launch time:", inst["LaunchTime"])

        print("Security groups:")
        for group in inst.get("SecurityGroups", []):
            print(f"  - {group['GroupName']} ({group['GroupId']})")

        print("Tags:")
        for tag in tags:
            print(f"  - {tag['Key']} = {tag['Value']}")

        # Add or update the Owner tag
        ec2.create_tags(
            Resources=[instance_id],
            Tags=[{"Key": "Owner", "Value": "youssef"}],
        )

        print("\nTag Owner=youssef added or updated.")

        # Retrieve the tags again to confirm the change
        updated = ec2.describe_instances(
            InstanceIds=[instance_id]
        )
        updated_inst = updated["Reservations"][0]["Instances"][0]

        print("Updated tags:")
        for tag in updated_inst.get("Tags", []):
            print(f"  - {tag['Key']} = {tag['Value']}")

    except Exception as e:
        print(f"[ERROR] {e}")



def cleanup_instances():
    try:
        # Find lab-created instances in the specified states
        response = ec2.describe_instances(
            Filters=[
                {
                    "Name": "tag:CreatedBy",
                    "Values": ["boto3-lab"],
                },
                {
                    "Name": "instance-state-name",
                    "Values": [
                        "pending",
                        "running",
                        "stopping",
                        "stopped",
                    ],
                },
            ]
        )

        # Collect instance IDs
        ids = [
            inst["InstanceId"]
            for reservation in response["Reservations"]
            for inst in reservation["Instances"]
        ]

        if not ids:
            print("No lab-created EC2 instances found.")
            return

        print("These instances will be terminated:")
        for instance_id in ids:
            print(f"  - {instance_id}")

        # Ask for confirmation before deleting instances
        confirmation = input("Type YES to confirm: ").strip()

        if confirmation != "YES":
            print("Cleanup cancelled.")
            return

        # Terminate the instances
        ec2.terminate_instances(InstanceIds=ids)

        print("Waiting for all instances to terminate ...")

        waiter = ec2.get_waiter("instance_terminated")
        waiter.wait(
            InstanceIds=ids,
            WaiterConfig={
                "Delay": 15,
                "MaxAttempts": 40,
            },
        )

        print(f"Terminated {len(ids)} instance(s).")

    except WaiterError:
        print("Timed out waiting for termination. Check the AWS Console.")

    except Exception as e:
        print(f"[ERROR] {e}")


MENU = """
=============================
        EC2 MANAGER
=============================
1. List instances
2. Launch instance
3. Start instance
4. Stop instance
5. Reboot instance
6. Describe instance
9. Cleanup instances
0. Exit
=============================
"""


ACTIONS = {
    "1": list_instances,
    "2": launch_instance,
    "3": start_instance,
    "4": stop_instance,
    "5": reboot_instance,
    "6": describe_instance,
    "9": cleanup_instances,
}


def main():
    while True:
        print(MENU)

        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye!")
            sys.exit(0)

        action = ACTIONS.get(choice)

        if action:
            action()
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()