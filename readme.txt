Here’s the full guide to deploying an AWS Lambda function with Terraform that can delete/recycle specific pods or all pods in any specified namespace within an EKS cluster.

Full Solution Overview

	1.	Set up IAM Role and Policy for Lambda with IRSA (IAM Roles for Service Accounts)
	2.	Define Kubernetes ServiceAccount, Role, and RoleBinding
	3.	Write and Deploy the Lambda Function using Terraform
	4.	Add Variables and EKS Module Configuration
	5.	Test the Lambda Function

Step 1: IAM Role and Policy Configuration for Lambda with IRSA

This IAM role will be assumed by the Lambda function and linked to a Kubernetes service account using IRSA, allowing it to manage pods in the specified namespaces.
	1.	Create a Terraform file named iam.tf:

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

# IAM Role for Lambda with EKS Access
resource "aws_iam_role" "lambda_role" {
  name = "LambdaEKSAccessRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      },
      {
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/id/${module.eks.cluster_id}"
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            "oidc.eks.${var.region}.amazonaws.com/id/${module.eks.cluster_id}:sub" = "system:serviceaccount:${var.namespace}:lambda-k8s-access"
          }
        }
      }
    ]
  })
}

# IAM Policy for Lambda to Describe EKS Cluster
resource "aws_iam_policy" "lambda_policy" {
  name = "LambdaEKSAccessPolicy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "eks:DescribeCluster"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach IAM Policy to the Role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

	•	Explanation:
	•	eks:DescribeCluster permission allows Lambda to fetch cluster details.
	•	sts:AssumeRoleWithWebIdentity allows the role to be assumed by Kubernetes service accounts via IRSA.

Step 2: Define Kubernetes ServiceAccount, Role, and RoleBinding

Set up Kubernetes resources to map the IAM role to a service account and give it permissions to manage pods.
	1.	Create a Terraform file named k8s_resources.tf:

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  token                  = data.aws_eks_cluster_auth.cluster.token
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
}

variable "namespaces" {
  type        = list(string)
  description = "List of namespaces where Lambda should have access to manage pods."
  default     = ["namespace1", "namespace2"]  # Add your actual namespaces here
}

# Create a ServiceAccount for Lambda in Each Namespace
resource "kubernetes_service_account" "lambda_k8s_access" {
  for_each = toset(var.namespaces)

  metadata {
    name      = "lambda-k8s-access"
    namespace = each.value
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.lambda_role.arn
    }
  }
}

# Role to Allow Pod Management in Each Namespace
resource "kubernetes_role" "pod_manipulator" {
  for_each = toset(var.namespaces)

  metadata {
    name      = "pod-manipulator"
    namespace = each.value
  }
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "delete"]
  }
}

# RoleBinding to Attach Role to ServiceAccount in Each Namespace
resource "kubernetes_role_binding" "lambda_pod_access" {
  for_each = toset(var.namespaces)

  metadata {
    name      = "lambda-pod-access"
    namespace = each.value
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.pod_manipulator[each.value].metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.lambda_k8s_access[each.value].metadata[0].name
    namespace = each.value
  }
}

	•	Explanation: This configuration sets up a service account, role, and role binding for each namespace in var.namespaces.

Step 3: Write and Deploy the Lambda Function with Terraform

	1.	Create lambda_function.py: This Lambda function code will delete pods based on the input parameters.

import os
import json
import boto3
from kubernetes import client, config
from kubernetes.client.rest import ApiException

region = os.getenv('AWS_REGION')
eks_cluster_name = os.getenv('EKS_CLUSTER_NAME')
debug = os.getenv('DEBUG', 'false').lower() == 'true'

eks_client = boto3.client('eks', region_name=region)

def get_eks_cluster_info():
    response = eks_client.describe_cluster(name=eks_cluster_name)
    return response['cluster']

def create_kube_config(cluster_info):
    kube_config = client.Configuration()
    kube_config.host = f"https://{cluster_info['endpoint']}"
    kube_config.verify_ssl = True
    kube_config.ssl_ca_cert = '/tmp/ca.crt'
    with open('/tmp/ca.crt', 'w') as ca_file:
        ca_file.write(cluster_info['certificateAuthority']['data'])
    kube_config.api_key['authorization'] = "Bearer " + os.getenv('KUBE_TOKEN')
    client.Configuration.set_default(kube_config)

def delete_pods(namespace, pod_name=None):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    if pod_name:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return f"Pod '{pod_name}' deleted in namespace '{namespace}'."
    else:
        pods = v1.list_namespaced_pod(namespace=namespace).items
        for pod in pods:
            v1.delete_namespaced_pod(name=pod.metadata.name, namespace=namespace)
        return f"All pods in namespace '{namespace}' deleted."

def lambda_handler(event, context):
    namespace = event.get('namespace')
    if not namespace:
        return {"statusCode": 400, "body": "Error: 'namespace' parameter is required."}
    
    pod_name = event.get('podName')
    delete_all = event.get('deleteAll', False)
    cluster_info = get_eks_cluster_info()
    create_kube_config(cluster_info)
    result = delete_pods(namespace, pod_name if not delete_all else None)
    return {"statusCode": 200, "body": result}


	2.	Zip the Lambda Function:

zip function.zip lambda_function.py


	3.	Create lambda.tf: This file defines the Lambda function resource in Terraform.

resource "aws_lambda_function" "delete_k8s_pods" {
  filename         = "function.zip"  # Path to your function.zip file
  function_name    = "delete_k8s_pods"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = filebase64sha256("function.zip")
  runtime          = "python3.8"

  environment {
    variables = {
      AWS_REGION       = var.region
      EKS_CLUSTER_NAME = module.eks.cluster_id
      DEBUG            = "true"
    }
  }
}

Step 4: Define Variables and EKS Module Configuration

	1.	Create variables.tf: Define variables for AWS region and namespaces.

variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-west-2"  # Replace with your AWS region
}

variable "namespaces" {
  type        = list(string)
  description = "List of namespaces where Lambda can manage pods"
  default     = ["namespace1", "namespace2"]
}


	2.	Add the EKS Cluster Data Sources in main.tf:

data "aws_eks_cluster" "cluster" {
  name = "your-eks-cluster-name"  # Replace with your EKS cluster name
}

data "aws_eks_cluster_auth" "cluster" {
  name = data.aws_eks_cluster.cluster.name
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = data.aws_eks_cluster.cluster.name
  cluster_endpoint = data.aws_eks_cluster.cluster.endpoint
  cluster_ca_cert  = data.aws_eks_cluster.cluster.certificate_authority.0.data
}

Step 5: Deploy and Test the Lambda Function

	1.	Initialize Terraform:

terraform init


	2.	Plan and Apply:

terraform plan
terraform apply

Confirm with yes when prompted.

	3.	Test the Lambda Function in the AWS Console:
	•	Go to the Lambda Console.
	•	Create test events with the following JSON to specify the namespace and podName (or use deleteAll).
Delete a specific pod:

{
  "namespace": "your-namespace",
  "podName": "your-pod-name"
}

Delete all pods in a namespace:

{
  "namespace": "your-namespace",
  "deleteAll": true
}


	•	Replace your-namespace and your-pod-name as needed.

This configuration allows the Lambda function to delete specific or all pods in any specified namespace, managed entirely through Terraform for secure and consistent deployment.