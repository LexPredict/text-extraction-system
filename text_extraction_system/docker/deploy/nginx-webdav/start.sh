#!/bin/sh

if [ -n "${USERNAME}" ] && [ -n "${PASSWORD}" ]
then
  echo "WebDav accepts requests from user: ${USERNAME}"
	htpasswd -bc /etc/nginx/htpasswd ${USERNAME} ${PASSWORD}
else
  echo "WebDav accepts requests with no authentication."
	sed -i 's%auth_basic "Restricted";% %g' /etc/nginx/conf.d/default.conf
	sed -i 's%auth_basic_user_file /etc/nginx/htpasswd;% %g' /etc/nginx/conf.d/default.conf
fi
exec nginx -g "daemon off;"