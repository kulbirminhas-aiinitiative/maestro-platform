#!/bin/bash

# User data script for EKS worker nodes
# This script configures the EKS worker nodes with optimizations and monitoring

set -euo pipefail

# Logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting EKS node bootstrap process..."

# Variables passed from Terraform
CLUSTER_NAME="${cluster_name}"
ENDPOINT="${endpoint}"
CA_CERTIFICATE="${ca_certificate}"
BOOTSTRAP_ARGUMENTS="${bootstrap_arguments}"

# Update system packages
yum update -y

# Install required packages
yum install -y \
    awscli \
    jq \
    htop \
    iotop \
    nfs-utils \
    amazon-cloudwatch-agent

# Configure CloudWatch agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "root"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "/aws/eks/${cluster_name}/node/messages",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/var/log/dmesg",
                        "log_group_name": "/aws/eks/${cluster_name}/node/dmesg",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/var/log/docker",
                        "log_group_name": "/aws/eks/${cluster_name}/node/docker",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/aws/eks/${cluster_name}/node/user-data",
                        "log_stream_name": "{instance_id}",
                        "timezone": "UTC"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "CWAgent",
        "metrics_collected": {
            "cpu": {
                "measurement": [
                    "cpu_usage_idle",
                    "cpu_usage_iowait",
                    "cpu_usage_user",
                    "cpu_usage_system"
                ],
                "metrics_collection_interval": 60,
                "totalcpu": false
            },
            "disk": {
                "measurement": [
                    "used_percent"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "diskio": {
                "measurement": [
                    "io_time"
                ],
                "metrics_collection_interval": 60,
                "resources": [
                    "*"
                ]
            },
            "mem": {
                "measurement": [
                    "mem_used_percent"
                ],
                "metrics_collection_interval": 60
            },
            "netstat": {
                "measurement": [
                    "tcp_established",
                    "tcp_time_wait"
                ],
                "metrics_collection_interval": 60
            },
            "swap": {
                "measurement": [
                    "swap_used_percent"
                ],
                "metrics_collection_interval": 60
            }
        }
    }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
    -s

# Enable CloudWatch agent service
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

# Configure kernel parameters for performance
cat >> /etc/sysctl.conf << EOF
# Network performance tuning
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 10

# Memory management
vm.swappiness = 1
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.max_map_count = 262144

# File system
fs.file-max = 2097152
fs.nr_open = 1048576

# Container runtime optimizations
kernel.pid_max = 4194304
EOF

# Apply sysctl changes
sysctl -p

# Configure ulimits
cat >> /etc/security/limits.conf << EOF
* soft nofile 1048576
* hard nofile 1048576
* soft nproc 1048576
* hard nproc 1048576
EOF

# Docker optimizations
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "live-restore": true,
    "max-concurrent-downloads": 10,
    "max-concurrent-uploads": 5,
    "storage-driver": "overlay2",
    "storage-opts": [
        "overlay2.override_kernel_check=true"
    ]
}
EOF

# Configure kubelet
mkdir -p /etc/kubernetes/kubelet
cat > /etc/kubernetes/kubelet/kubelet-config.json << EOF
{
    "kind": "KubeletConfiguration",
    "apiVersion": "kubelet.config.k8s.io/v1beta1",
    "address": "0.0.0.0",
    "authentication": {
        "anonymous": {
            "enabled": false
        },
        "webhook": {
            "cacheTTL": "2m0s",
            "enabled": true
        },
        "x509": {
            "clientCAFile": "/etc/kubernetes/pki/ca.crt"
        }
    },
    "authorization": {
        "mode": "Webhook",
        "webhook": {
            "cacheAuthorizedTTL": "5m0s",
            "cacheUnauthorizedTTL": "30s"
        }
    },
    "clusterDomain": "cluster.local",
    "cpuManagerPolicy": "none",
    "eventRecordQPS": 50,
    "evictionHard": {
        "imagefs.available": "15%",
        "memory.available": "300Mi",
        "nodefs.available": "15%",
        "nodefs.inodesFree": "10%"
    },
    "evictionPressureTransitionPeriod": "5m0s",
    "failSwapOn": false,
    "fileCheckFrequency": "20s",
    "hairpinMode": "promiscuous-bridge",
    "healthzBindAddress": "127.0.0.1",
    "healthzPort": 10248,
    "httpCheckFrequency": "20s",
    "imageGCHighThresholdPercent": 85,
    "imageGCLowThresholdPercent": 80,
    "imageMinimumGCAge": "2m0s",
    "kubeAPIBurst": 100,
    "kubeAPIQPS": 50,
    "makeIPTablesUtilChains": true,
    "maxOpenFiles": 1000000,
    "maxPods": 110,
    "nodeStatusReportFrequency": "10s",
    "nodeStatusUpdateFrequency": "10s",
    "oomScoreAdj": -999,
    "podPidsLimit": 4096,
    "port": 10250,
    "readOnlyPort": 0,
    "registryBurst": 10,
    "registryPullQPS": 5,
    "resolvConf": "/etc/resolv.conf",
    "rotateCertificates": true,
    "runtimeRequestTimeout": "2m0s",
    "serializeImagePulls": false,
    "staticPodPath": "/etc/kubernetes/manifests",
    "streamingConnectionIdleTimeout": "4h0m0s",
    "syncFrequency": "1m0s",
    "volumeStatsAggPeriod": "1m0s"
}
EOF

# Create directories for monitoring
mkdir -p /opt/node-exporter
mkdir -p /var/log/pods

# Install Node Exporter for Prometheus monitoring
NODE_EXPORTER_VERSION="1.6.1"
cd /tmp
curl -LO "https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
tar xvf "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz"
cp "node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter" /opt/node-exporter/
rm -rf "node_exporter-${NODE_EXPORTER_VERSION}*"

# Create Node Exporter service
cat > /etc/systemd/system/node-exporter.service << EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=root
Group=root
Type=simple
ExecStart=/opt/node-exporter/node_exporter \
    --web.listen-address=:9100 \
    --path.rootfs=/host \
    --collector.filesystem.mount-points-exclude="^/(sys|proc|dev|host|etc|rootfs/var/lib/docker/containers|rootfs/var/lib/docker/overlay2|rootfs/run/docker/netns|rootfs/var/lib/docker/aufs)($$|/)" \
    --collector.systemd \
    --collector.processes

[Install]
WantedBy=multi-user.target
EOF

# Enable and start Node Exporter
systemctl daemon-reload
systemctl enable node-exporter
systemctl start node-exporter

# Configure log rotation
cat > /etc/logrotate.d/eks-node << EOF
/var/log/pods/*/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        /bin/kill -USR1 \$(cat /var/run/rsyslogd.pid 2> /dev/null) 2> /dev/null || true
    endscript
}

/var/log/user-data.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

# Create a startup script for post-boot optimizations
cat > /opt/post-boot-optimization.sh << 'EOF'
#!/bin/bash
# Post-boot optimization script

# Wait for the system to fully boot
sleep 30

# Optimize CPU governor
echo performance > /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true

# Optimize I/O scheduler for NVMe and SSD
for disk in /sys/block/nvme*; do
    if [ -e "$disk/queue/scheduler" ]; then
        echo mq-deadline > "$disk/queue/scheduler"
    fi
done

for disk in /sys/block/sd*; do
    if [ -e "$disk/queue/scheduler" ]; then
        echo deadline > "$disk/queue/scheduler"
    fi
done

# Optimize network interface settings
for interface in $(ls /sys/class/net/ | grep -v lo); do
    ethtool -G "$interface" rx 4096 tx 4096 2>/dev/null || true
    ethtool -K "$interface" gso on gro on tso on 2>/dev/null || true
done

# Clear page cache if memory usage is high
MEMORY_USAGE=$(free | grep Mem | awk '{print ($3/$2) * 100.0}')
if (( $(echo "$MEMORY_USAGE > 85" | bc -l) )); then
    echo 1 > /proc/sys/vm/drop_caches
fi

echo "Post-boot optimization completed" >> /var/log/user-data.log
EOF

chmod +x /opt/post-boot-optimization.sh

# Create systemd service for post-boot optimization
cat > /etc/systemd/system/post-boot-optimization.service << EOF
[Unit]
Description=Post-boot optimization
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/opt/post-boot-optimization.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl enable post-boot-optimization

# Bootstrap the EKS node
echo "Bootstrapping EKS node..."
/etc/eks/bootstrap.sh "$CLUSTER_NAME" $BOOTSTRAP_ARGUMENTS

# Verify kubelet is running
systemctl status kubelet --no-pager

# Install additional monitoring tools
# Install cadvisor for container metrics
docker run \
    --volume=/:/rootfs:ro \
    --volume=/var/run:/var/run:ro \
    --volume=/sys:/sys:ro \
    --volume=/var/lib/docker/:/var/lib/docker:ro \
    --volume=/dev/disk/:/dev/disk:ro \
    --publish=8080:8080 \
    --detach=true \
    --name=cadvisor \
    --privileged \
    --device=/dev/kmsg \
    --restart=unless-stopped \
    gcr.io/cadvisor/cadvisor:latest

# Create health check script
cat > /opt/health-check.sh << 'EOF'
#!/bin/bash
# Node health check script

# Check if kubelet is running
if ! systemctl is-active --quiet kubelet; then
    echo "ERROR: kubelet is not running"
    exit 1
fi

# Check if node is ready
if ! kubectl get nodes $(hostname) --no-headers | grep -q Ready; then
    echo "ERROR: Node is not ready"
    exit 1
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
    echo "WARNING: Disk usage is ${DISK_USAGE}%"
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{print ($3/$2) * 100.0}')
if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
    echo "WARNING: Memory usage is ${MEMORY_USAGE}%"
fi

echo "Node health check passed"
EOF

chmod +x /opt/health-check.sh

# Create cron job for health checks
echo "*/5 * * * * /opt/health-check.sh >> /var/log/health-check.log 2>&1" > /var/spool/cron/root

# Final system optimization
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag

# Configure entropy for better random number generation
echo "HRNGDEVICE=/dev/urandom" >> /etc/default/rng-tools
systemctl enable rng-tools
systemctl start rng-tools

# Signal completion
echo "EKS node bootstrap completed successfully" >> /var/log/user-data.log
echo "Node $(hostname) is ready for workloads" >> /var/log/user-data.log

# Send signal to CloudFormation (if using CFN)
# /opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} --resource NodeGroup --region ${AWS::Region}

exit 0