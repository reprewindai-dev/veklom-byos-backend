
APP=app-ywg7bi2al9ycicngyymuigio
DB=postgres-ywg7bi2al9ycicngyymuigio

echo "### \`hostname\`"
echo "\`\`\`bash"
hostname
echo "\`\`\`"

echo "### \`docker ps | grep metamcp\`"
echo "\`\`\`bash"
docker ps | grep -E "CONTAINER|ywg7bi2al9ycicngyymuigio"
echo "\`\`\`"

echo "### \`docker inspect <metamcp-app-container>\`"
echo "\`\`\`json"
docker inspect $APP | jq ".[0] | del(.Config.Env, .ContainerConfig.Env)"
echo "\`\`\`"

echo "### \`docker inspect <metamcp-postgres-container>\`"
echo "\`\`\`json"
docker inspect $DB | jq ".[0] | del(.Config.Env, .ContainerConfig.Env)"
echo "\`\`\`"

echo "### \`env | grep -E 'DATABASE|POSTGRES|HOST|PORT|URL'\`"
echo "\`\`\`bash"
docker exec $APP env | grep -E "DATABASE|POSTGRES|HOST|PORT|URL" | sed "s/=.*/=<REDACTED>/g"
echo "\`\`\`"

echo "### \`getent hosts postgres db\`"
echo "\`\`\`bash"
docker exec $APP getent hosts postgres db || echo "Command failed or empty"
echo "\`\`\`"

echo "### \`docker-compose.yml\` (Redacted)"
echo "\`\`\`yaml"
cat /data/coolify/services/ywg7bi2al9ycicngyymuigio/docker-compose.yml | sed -E "s/POSTGRES_USER:.*/POSTGRES_USER: '<REDACTED>'/g" | sed -E "s/POSTGRES_PASSWORD:.*/POSTGRES_PASSWORD: '<REDACTED>'/g" | sed -E "s/DATABASE_URL:.*/DATABASE_URL: '<REDACTED>'/g" | sed -E "s/BETTER_AUTH_SECRET:.*/BETTER_AUTH_SECRET: '<REDACTED>'/g"
echo "\`\`\`"
