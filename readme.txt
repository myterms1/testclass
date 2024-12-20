Deployment Instructions
Step 1: Install Dependencies
Install Node.js on your local machine if not already installed.

Download it from Node.js official website. https://nodejs.org/en
Create a folder named delete-pods and navigate to it:
mkdir delete-pods
cd delete-pods

Initialize the project and install dependencies:
npm init -y
npm install @aws-sdk/client-eks @kubernetes/client-node




Step 2: Package for Lambda
Copy the script above into a file named index.js inside the delete-pods folder.

Zip the contents of the delete-pods folder:
zip -r deployment.zip node_modules index.js package.json


Step 3: Set Environment Variables
Set the following environment variables in your Lambda function:

Testing the Script
Set the environment variables:

EKS_CLUSTER_NAME: Your EKS cluster name.
K8S_NAMESPACE: Namespace for pods (e.g., default).
Use the following test event

{
    "pods": [
        { "name": "pod1", "namespace": "default" },
        { "name": "pod2", "namespace": "test" }
    ]
}


Important Notes
Ensure the Lambda function role has permissions for:

eks:DescribeCluster
sts:GetCallerIdentity
Kubernetes API operations via AWS IAM Authenticator.
If the Lambda execution environment cannot access your cluster, check your VPC configuration and ensure that the Lambda function has appropriate network access to the Kubernetes API endpoint.

This script avoids using the AWS CLI to generate tokens, relying solely on the AWS SDK, which ensures compatibility with Lambda environments


