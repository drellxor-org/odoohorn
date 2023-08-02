#!/bin/bash

pip install -r requirements.txt


if [ -v REMOTE_DEBUG ]; then
    export PATH="${PATH}:/var/lib/odoo/.local/bin"
    pip install "${REMOTE_DEBUG}"
    pip install pydevd-odoo
    REMOTE_DEBUG_GATEWAY_IP=$(printf "%d.%d.%d.%d" $(awk '$2 == 00000000 && $7 == 00000000 { for (i = 8; i >= 2; i=i-2) { print "0x" substr($3, i-1, 2) } }' /proc/net/route))
    echo "Remote debug server IP is: $REMOTE_DEBUG_GATEWAY_IP"
    REMOTE_DEBUG_PYTHON_CODE=$(echo "\nimport os\nremote_debug = os.getenv(\"REMOTE_DEBUG\", 0)\nif remote_debug:\n   import pydevd\n   try:\n      pydevd.settrace('${REMOTE_DEBUG_GATEWAY_IP}', port=5666, stdoutToServer=True, stderrToServer=True, suspend=False)\n   except:\n      ...")
    sed -i "2a\\$REMOTE_DEBUG_PYTHON_CODE" /usr/lib/python3/dist-packages/odoo/__init__.py
fi


echo "MODULES_TO_INIT=${MODULES_TO_INIT}"
echo "MODULES_TO_UPDATE=${MODULES_TO_UPDATE}"
echo "MODULES_TO_UNINSTALL=${MODULES_TO_UNINSTALL}"
echo "POSTGRES_DB=${POSTGRES_DB}"

exec odoo --database=${POSTGRES_DB} --init=${MODULES_TO_INIT} --update=${MODULES_TO_UPDATE}

exit 1
