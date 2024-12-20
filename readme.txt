Step 1: Install Node.js
Check if Node.js is already installed:

node -v
npm -v
If you see version numbers for both, Node.js is already installed.

Download and Install Node.js:

Go to the Node.js official website.
Download the LTS version (recommended for most users).
Install it by following the installer instructions for your operating system.
Verify Installation: After installation, verify it by running:

node -v
npm -v
Step 2: Set Up Your Lambda Function
Create a Directory: Create a new folder for your Lambda function code:

mkdir my-lambda-function
cd my-lambda-function
Create the index.js File: Create a file named index.js (this will hold your Lambda function):


touch index.js
Copy the JavaScript Code: Paste the JavaScript function (provided earlier) into the index.js file.

Step 3: Initialize Node.js Project
Run npm init to Create package.json:


npm init -y
This will generate a basic package.json file for your project.

Install Required Dependencies: Install the necessary Node.js packages for the function:


npm install @aws-sdk/client-eks @kubernetes/client-node
Verify Installed Dependencies: Ensure that the node_modules folder is created, and the dependencies are listed in package.json.

Step 4: Package the Lambda Function
Zip the Files: To package the Lambda function, include the following files and folders:

index.js (your Lambda function code)
package.json (Node.js configuration)
node_modules (installed dependencies)
Use the following command to create the ZIP file:


zip -r deployment.zip index.js package.json node_modules
Verify the ZIP File: Check that the deployment.zip file is created:


ls
You should see deployment.zip in the directory.

Step 5: Your Deployment ZIP is Ready
The deployment.zip file now contains:

index.js
package.json
The node_modules folder with all dependencies.
This file is ready to be uploaded to the AWS Lambda console.

Additional Notes:
If you are using a specific Node.js version, ensure it matches the runtime version in the Lambda function configuration.
If you need to test locally, install the aws-sdk package globally:
bash
Copy code
npm install -g aws-sdk



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


