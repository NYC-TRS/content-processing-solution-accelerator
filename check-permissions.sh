#!/bin/bash

# Check your role assignments at subscription level
echo "=== Your Role Assignments at Subscription Level ==="
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) \
  --scope /subscriptions/2bd8d406-aea5-4c75-85f5-c8428d262952 \
  --output table

echo ""
echo "=== Checking if you have roleAssignments/write permission ==="
az role definition list --name "Owner" --query "[].permissions[].actions" -o json
az role definition list --name "User Access Administrator" --query "[].permissions[].actions" -o json
az role definition list --name "Contributor" --query "[].permissions[].actions" -o json

echo ""
echo "=== Your current user info ==="
az ad signed-in-user show --query "{UPN:userPrincipalName, ObjectId:id}" -o table
