import time
import boto3
from pymongo import MongoClient

# Crea una instancia del cliente EC2 de AWS
ec2_client = boto3.client('ec2')

def create_instances(count):
    # Crea nuevas instancias EC2
    response = ec2_client.run_instances(
        ImageId='ami-0f09de67419a5c3c1',
        InstanceType='t2.micro',
        MinCount=count,
        MaxCount=count
    )
    instance_ids = []
    configuration = collection.find_one()
    for instance in response["Instances"]:
        instance_ids.append(instance["InstanceId"])
        newHost = {
            "id_instance":instance["InstanceId"],
            "ip":get_public_ip(instance["InstanceId"])
        }
        configuration["hosts"].append(newHost)
    collection.update_one({'_id': configuration['_id']}, {'$set': configuration})
    print(f'Se han creado {count} nuevas instancias: {instance_ids}')

def get_public_ip(instance_id):
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    public_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
    return public_ip

def terminate_instances(count):
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ]
    )
    instances = response['Reservations']
    instances_to_terminate = instances[:count]
    instance_ids = []
    configuration = collection.find_one()
    for i in range(0, count):
        instance_ids.append(instances_to_terminate[i]['Instances'][0]['InstanceId'])
        hosts_filtrados = [host for host in configuration["hosts"] if host['id_instance'] != instance_ids[-1]]
        configuration["hosts"] = hosts_filtrados
    collection.update_one({'_id': configuration['_id']}, {'$set': configuration})

    # Termina las instancias seleccionadas
    response = ec2_client.terminate_instances(
        InstanceIds=instance_ids
    )
    print(f'Se han terminado {count} instancias: {instance_ids}')

def monitor_cpu_usage():
    return collection.find_one()["average_memory"]

def scale_instances():
    # Obtiene el número actual de instancias activas
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ]
    )
    try:
        instance_count = len(response['Reservations'])
    except:
        instance_count = 0
    cpu_usage = monitor_cpu_usage()

    # Realiza la lógica de escalado
    if cpu_usage > cpu_threshold and instance_count < max_instances:
        new_instance_count = min(max_instances, instance_count * scale_up_factor)
        if new_instance_count == 0:
            new_instance_count = 1
        instances_to_create = new_instance_count - instance_count
        create_instances(instances_to_create)
    elif cpu_usage < cpu_threshold and instance_count > min_instances:
        instances_to_terminate = instance_count - min_instances
        terminate_instances(instances_to_terminate)

if __name__ == '__main__':
    global client, database, collection, min_instances, max_instances, cpu_threshold, scale_up_factor, scale_down_factor
    client = MongoClient("mongodb://localhost:27017")
    database = client["ASG"]
    collection = database["config"]
    config = collection.find_one()
    min_instances = config["min_instances"]
    max_instances = config["max_instances"]
    cpu_threshold = config["cpu_threshold"]
    scale_up_factor = config["scale_up_factor"]
    scale_down_factor = config["scale_down_factor"]
    while True:
        # Ejecuta la lógica de escalado cada X segundos
        scale_instances()
        time.sleep(30)  # Espera 60 segundos antes de la siguiente iteración
