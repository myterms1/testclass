# Use AWS Lambda base image for Python 3.9
FROM public.ecr.aws/lambda/python:3.9

ARG AWS_IAM_AUTH_VERSION=0.6.14
ARG AWS_IAM_AUTH_PLATFORM=linux_amd64

# Add trust for Zscaler CA
RUN curl -kfsSL https://github.company.com/certfix/master/zscaler.pem -o /etc/pki/ca-trust/source/zscaler.pem \
  && update-ca-trust extract

# Install AWS IAM Authenticator
RUN mkdir -p /usr/local/bin \
  && curl --cacert /etc/pki/ca-trust/source/zscaler.pem \
      -fsSL https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/download/v${AWS_IAM_AUTH_VERSION}/aws-iam-authenticator_${AWS_IAM_AUTH_VERSION}_${AWS_IAM_AUTH_PLATFORM} \
      -o /usr/local/bin/aws-iam-authenticator \
  && chmod a+rx /usr/local/bin/aws-iam-authenticator

# Copy the Python script and requirements
COPY recycling_pod_script.py ${LAMBDA_TASK_ROOT}/
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install required Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# Set the Lambda handler
CMD ["recycling_pod_script.lambda_handler"]
