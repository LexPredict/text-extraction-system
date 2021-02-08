FROM nginx:1.19.6

RUN apt-get update && apt-get dist-upgrade -y && apt-get install -y nginx-extras apache2-utils
RUN mkdir /data && chown www-data:www-data /data

EXPOSE 80
COPY nginx.conf /etc/nginx/nginx.conf
COPY start.sh /
RUN chmod +x start.sh

ENTRYPOINT ["./start.sh"]