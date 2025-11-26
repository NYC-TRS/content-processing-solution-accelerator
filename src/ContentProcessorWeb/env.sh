#!/bin/sh
# Replace both APP_* and REACT_APP_* placeholders
for i in $(env | grep ^APP_)
do
    key=$(echo $i | cut -d '=' -f 1)
    value=$(echo $i | cut -d '=' -f 2-)
    echo "Replacing: $key=$value"

    # Replace APP_XXX placeholder (e.g., APP_API_SCOPE)
    find /usr/share/nginx/html -type f \( -name "*.js" -o -name "*.html" \) \
      -exec sed -i "s|${key}|${value}|g" '{}' +

    # Also replace REACT_APP_XXX placeholder (e.g., REACT_APP_API_SCOPE)
    react_key="REACT_${key}"
    echo "Replacing: $react_key=$value"
    find /usr/share/nginx/html -type f \( -name "*.js" -o -name "*.html" \) \
      -exec sed -i "s|${react_key}|${value}|g" '{}' +
done
echo 'Environment variable replacement complete'