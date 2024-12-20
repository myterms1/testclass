const { EKSClient, DescribeClusterCommand } = require("@aws-sdk/client-eks");
const k8s = require("@kubernetes/client-node");

// Define the region in the script, as AWS_REGION cannot be used in Lambda
const region = "us-east-1";

// Read cluster name and namespace from environment variables
const eksClusterName = process.env.EKS_CLUSTER_NAME;
const k8sNamespace = process.env.K8S_NAMESPACE;

exports.handler = async (event) => {
    console.log("Starting EKS pod deletion Lambda...");

    if (!eksClusterName) {
        throw new Error("EKS_CLUSTER_NAME environment variable is not set.");
    }

    if (!k8sNamespace) {
        throw new Error("K8S_NAMESPACE environment variable is not set.");
    }

    try {
        // Step 1: Fetch EKS cluster details
        const eksClient = new EKSClient({ region });
        const describeClusterParams = { name: eksClusterName };
        const describeClusterCommand = new DescribeClusterCommand(describeClusterParams);
        const describeClusterResponse = await eksClient.send(describeClusterCommand);
        const eksCluster = describeClusterResponse.cluster;

        console.log("EKS cluster details fetched successfully.");

        // Step 2: Create Kubernetes configuration
        const k8sCluster = {
            name: eksClusterName,
            server: eksCluster.endpoint,
            caData: eksCluster.certificateAuthority.data,
        };

        const k8sUser = {
            name: "lambda-auth",
            exec: {
                apiVersion: "client.authentication.k8s.io/v1beta1",
                command: "aws-iam-authenticator",
                args: ["token", "-i", eksClusterName],
                env: [{ name: "AWS_REGION", value: region }],
            },
        };

        const k8sContext = {
            name: "eks",
            cluster: k8sCluster.name,
            user: k8sUser.name,
        };

        // Step 3: Load Kubernetes config
        const kubeConfig = new k8s.KubeConfig();
        kubeConfig.loadFromOptions({
            clusters: [k8sCluster],
            contexts: [k8sContext],
            users: [k8sUser],
            currentContext: k8sContext.name,
        });

        console.log("Kubernetes configuration loaded successfully.");

        // Step 4: Delete pods from the cluster
        const coreV1Api = kubeConfig.makeApiClient(k8s.CoreV1Api);

        for (const pod of event.pods || []) {
            const namespace = pod.namespace || k8sNamespace;
            const podName = pod.name;

            if (!namespace || !podName) {
                console.warn("Invalid pod details. Skipping...");
                continue;
            }

            console.log(`Deleting pod: ${podName} in namespace: ${namespace}`);
            await coreV1Api.deleteNamespacedPod(podName, namespace);
            console.log(`Pod ${podName} deleted successfully.`);
        }

        return {
            status: "success",
            message: "All specified pods have been deleted.",
        };
    } catch (error) {
        console.error("Error occurred while processing:", error);
        return {
            status: "error",
            message: error.message,
        };
    }
};
