FROM nginx:latest

RUN apt-get update && apt-get install -y php-fpm

COPY default.conf /etc/nginx/conf.d/default.conf

COPY www.conf /etc/php/8.2/fpm/pool.d/www.conf

RUN mkdir -p /usr/share/nginx/html

COPY index.html /usr/share/nginx/html
COPY index.php /usr/share/nginx/html

COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
