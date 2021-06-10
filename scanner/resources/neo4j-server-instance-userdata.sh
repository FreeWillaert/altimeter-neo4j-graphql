#!/bin/bash -x


# This script starts at the launch of a VM, and handles final cluster coordination.
sudo /bin/rm -f /etc/neo4j/password-reset.log
LOGFILE=/home/ubuntu/setup.log

echo `date` 'Preparing Standalone Neo4j Node' | tee -a $LOGFILE

/bin/systemctl stop neo4j.service 2>&1 | tee -a $LOGFILE
export API=http://169.254.169.254/latest/
export EC2_AVAIL_ZONE=$(curl --silent $API/meta-data/placement/availability-zone)
export EC2_INSTANCE_ID=$(curl -s $API/meta-data/instance-id)
export EC2_REGION=$(curl -s $API/dynamic/instance-identity/document | jq -r .region)
export EC2_LOCAL_IP=$(curl -s $API/meta-data/local-ipv4)
export ROOT_DISK_ID=$(aws ec2 describe-volumes --filters Name=attachment.instance-id,Values=${EC2_INSTANCE_ID} Name=attachment.device,Values=/dev/sda1 --query 'Volumes[*].[VolumeId]' --region=${EC2_REGION} --out text | cut -f 1)

# Neo4j AMI comes with a very old AWS CLI, so first update it.
sudo apt-get update
apt install unzip  2>&1 | tee -a $LOGFILE
curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"  2>&1 | tee -a $LOGFILE
unzip awscli-bundle.zip  2>&1 | tee -a $LOGFILE
./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws  2>&1 | tee -a $LOGFILE
/usr/local/bin/aws --version 2>&1 | tee -a $LOGFILE

export databaseNeo4jPassword=$(/usr/local/bin/aws --region eu-west-1 secretsmanager get-secret-value --secret-id [[NEO4J_USER_SECRET_NAME]] --query SecretString --output text)

env | tee -a $LOGFILE

# Tag volumes, which CloudFormation does not allow
# Root volume: /dev/sda
aws ec2 create-tags --resources $ROOT_DISK_ID --tags Key=Name,Value="Root Neo4j Vol for $EC2_INSTANCE_ID" --region ${EC2_REGION} 2>&1 | tee -a $LOGFILE

echo `date` 'Preparing neo4j service...' | tee -a $LOGFILE
/bin/rm -rf /var/lib/neo4j/data/databases/graph.db/ 2>&1 | tee -a $LOGFILE

/usr/bin/neo4j-admin set-initial-password $databaseNeo4jPassword

# Install neosemantics plugin
wget https://github.com/neo4j-labs/neosemantics/releases/download/4.2.0.1/neosemantics-4.2.0.1.jar -P /var/lib/neo4j/plugins
echo "dbms.security.procedures.unrestricted=n10s.*" >> /etc/neo4j/neo4j.conf
 
/bin/systemctl start neo4j.service 2>&1 | tee -a $LOGFILE

# TODO: Why doesn't 127.0.0.1 work with cypher-shell (not possible to connect to 127.0.0.1 on port 7687)
# TODO: Some or all of these command may need to be executed again after a db clean and re-import. Check out how to handle this.

# Prepare database for RDF import
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CREATE CONSTRAINT n10s_unique_uri ON (r:Resource) ASSERT r.uri IS UNIQUE"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.graphconfig.init({handleVocabUris: 'SHORTEN',handleMultival: 'OVERWRITE',handleRDFTypes: 'LABELS'})"

# Prepare RDF namespace prefixes
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('dynamodb', 'alti:aws:dynamodb:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('support', 'alti:aws:support:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('rds', 'alti:aws:rds:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('guardduty', 'alti:aws:guardduty:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('lambda', 'alti:aws:lambda:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('s3', 'alti:aws:s3:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('kms', 'alti:aws:kms:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('cloudtrail', 'alti:aws:cloudtrail:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('elb', 'alti:aws:elb:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('elbv2', 'alti:aws:elbv2:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('events', 'alti:aws:events:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('iam', 'alti:aws:iam:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('ec2', 'alti:aws:ec2:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('alti', 'alti:');"
cypher-shell -u neo4j -p $databaseNeo4jPassword -a $EC2_LOCAL_IP "CALL n10s.nsprefixes.add('aws', 'alti:aws:');"

# Install the CloudWatch Agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Create amazon-cloudwatch-agent.json in /opt/aws/amazon-cloudwatch-agent/etc$
echo '{
  "agent": {
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/neo4j/debug.log",
            "log_group_name": "/neo4j/logs/debug",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC",
            "timestamp_format": "%Y-%m-%d %H:%M:%S.%f%z",
            "multi_line_start_pattern": "{timestamp_format}"
          },
          {
            "file_path": "/var/log/neo4j/query.log",
            "log_group_name": "/neo4j/logs/query",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC",
            "timestamp_format": "%Y-%m-%d %H:%M:%S.%f%z",
            "multi_line_start_pattern": "{timestamp_format}"
          },
          {
            "file_path": "/var/log/neo4j/security.log",
            "log_group_name": "/neo4j/logs/security",
            "log_stream_name": "{instance_id}",
            "timezone": "UTC",
            "timestamp_format": "%Y-%m-%d %H:%M:%S.%f%z",
            "multi_line_start_pattern": "{timestamp_format}"
          }
        ]
      }
    }
  }
}' | sudo tee -a /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a fetch-config -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Loop waiting for neo4j service to start.
while true; do
    if curl -s -I http://localhost:7474 | grep '200 OK'; then
        echo `date` 'Startup complete ' | tee -a $LOGFILE
        break
    fi

    echo `date` 'Waiting for neo4j to come up' 2>&1 | tee -a $LOGFILE
    sleep 1
done