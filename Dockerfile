# Use AWS Lambda Python Base Image
FROM public.ecr.aws/lambda/python:3.11

# Arguments for AWS IAM Authenticator
ARG AWS_IAM_AUTH_VERSION=0.6.14
ARG AWS_IAM_AUTH_PLATFORM=linux_amd64

# Add Zscaler Certificate to Trusted CA Certificates
COPY zscaler.pem /etc/ssl/certs/zscaler.pem
RUN cat /etc/ssl/certs/zscaler.pem >> /etc/ssl/certs/ca-certificates.crt \
    && yum install -y ca-certificates curl unzip vim \
    && update-ca-trust extract

# Install AWS IAM Authenticator
RUN mkdir -p /usr/local/bin \
  && curl --cacert /etc/ssl/certs/ca-certificates.crt \
      -fsSL https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/download/v${AWS_IAM_AUTH_VERSION}/aws-iam-authenticator_${AWS_IAM_AUTH_VERSION}_${AWS_IAM_AUTH_PLATFORM} \
      -o /usr/local/bin/aws-iam-authenticator \
  && chmod a+rx /usr/local/bin/aws-iam-authenticator

# Install AWS CLI v2
RUN curl --cacert /etc/ssl/certs/ca-certificates.crt \
      -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" \
      -o "awscliv2.zip" \
  && unzip awscliv2.zip \
  && ./aws/install \
  && rm -rf aws awscliv2.zip

# Copy Python Lambda Function Code and Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY recycling_pod_script.py ${LAMBDA_TASK_ROOT}/

# Set the Lambda Handler
CMD [ "recycling_pod_script.lambda_handler" ]
