#!/bin/bash

bucket="honeypot-logs-2025"
timestamp=$ (date +"%Y-%m-%d_%H-%M-%S")

logs_src="$ home/cowrie/var/log/cowrie/"
downloads_src="$ home/cowrie/var/lib/cowrie/downloads/"

logs_dest="s3://$ bucket/cowrie/logs/$ timestamp/"
downloads_dest="s3://$ bucket/cowrie/downloads/$ timestamp/"

echo "Uploading Cowrie logs to $ logs_dest ..."
aws s3 cp "$ logs_src" "$ logs_dest" --recursive

echo "Uploading Cowrie downloads to $ downloads_dest ..."
aws s3 cp "$ downloads_src" "$ downloads_dest" --recursive

echo "Upload complete!"