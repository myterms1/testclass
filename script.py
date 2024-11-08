import os
import json
import boto3
import time
from kubernetes import client, config
from kubernetes.client import V1ObjectMeta, V1Job, V1JobSpec

# Load environment variables
region = os.getenv('AWS_REGION')
eks_cluster_name = os.getenv('EKS_CLUSTER_NAME')
k8s_namespace = os.getenv('K8S_NAMESPACE')
k8s_configmap = os.getenv('K8S_CONFIGMAP')
k8s_cronjob = os.getenv('K8S_CRONJOB')
debug = os.getenv('DEBUG', 'false').lower() == 'true'

# Set up AWS and Kubernetes clients
eks_client = boto3.client('eks', region_name=region)

def serialize(json_obj):
    """Helper function to serialize JSON for logging."""
    return json.dumps(json_obj, indent=2)

def set_result(status_code, message):
    """Function to set and return the result with a status code and message."""
    return {"statusCode": status_code, "message": message}

def get_eks_cluster_info():
    """Fetches EKS cluster information for authentication."""
    try:
        response = eks_client.describe_cluster(name=eks_cluster_name)
        cluster_info = response['cluster']
        if debug:
            print("Got EKS cluster info:", serialize(cluster_info))
        return cluster_info
    except Exception as e:
        print("Error fetching EKS cluster info:", e)
        return None

def create_kube_config(cluster_info):
    """Creates Kubernetes configuration for authentication with the EKS cluster."""
    kube_config = client.Configuration()
    kube_config.host = f"https://{cluster_info['endpoint']}"
    kube_config.verify_ssl = True
    kube_config.ssl_ca_cert = '/tmp/ca.crt'

    with open('/tmp/ca.crt', 'w') as ca_file:
        ca_file.write(cluster_info['certificateAuthority']['data'])
    
    kube_config.api_key['authorization'] = "Bearer " + os.getenv('KUBE_TOKEN')
    client.Configuration.set_default(kube_config)

def create_job_from_cronjob():
    """Reads a Kubernetes cronjob template and creates a new job based on it."""
    try:
        # Load Kubernetes config and initialize API client
        config.load_kube_config()
        k8s_batch_v1 = client.BatchV1Api()
        k8s_apps_v1 = client.AppsV1Api()

        # Fetch the CronJob spec to use as template
        cronjob = k8s_batch_v1.read_namespaced_cron_job(name=k8s_cronjob, namespace=k8s_namespace)
        cronjob_spec = cronjob.spec.job_template.spec

        # Generate a unique job name
        job_name = f"{k8s_configmap}-manual-{int(time.time())}"
        metadata = V1ObjectMeta(name=job_name, annotations={"cronjob.kubernetes.io/instantiate": "manual"})

        # Create the job
        job_spec = V1JobSpec(template=cronjob_spec.template)
        job = V1Job(api_version="batch/v1", kind="Job", metadata=metadata, spec=job_spec)
        job_creation_response = k8s_batch_v1.create_namespaced_job(namespace=k8s_namespace, body=job)
        
        if debug:
            print("Job creation response:", serialize(job_creation_response.to_dict()))
        
        return set_result(0, f"Success: Job {job_name} created.")
    except Exception as e:
        print("Error creating job:", e)
        return set_result(2, "Error: Processing failure. See logs for more info.")

def lambda_handler(event, context):
    """Main handler function."""
    if debug:
        print("FET batch job trigger")
        print("Event:", event)
        print("Context:", context)

    try:
        # Input validation
        job_config = event.get('jobConfig', {})
        xms_job_name = job_config.get('XmsJobName')
        xms_command_line = job_config.get('XmsCommandLine')

        if xms_job_name and xms_command_line:
            # Fetch EKS cluster information
            cluster_info = get_eks_cluster_info()
            if not cluster_info:
                return set_result(1, "Error: Failed to get EKS cluster information.")

            # Create Kubernetes config
            create_kube_config(cluster_info)
            
            # Create the job from the CronJob template
            result = create_job_from_cronjob()
            return result
        else:
            print("Invalid input")
            return set_result(3, "Error: Invalid input.")
    except Exception as error:
        print("Error:", error)
        return set_result(2, "Error: Processing failure. See logs for more info.")