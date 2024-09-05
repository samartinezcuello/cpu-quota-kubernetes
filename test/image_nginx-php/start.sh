#!/bin/sh

# Iniciar PHP-FPM en segundo plano
php-fpm8.2 &

# Esperar unos segundos para asegurarse de que PHP-FPM está en ejecución
sleep 5

# Iniciar Nginx en primer plano
nginx -g 'daemon off;'

