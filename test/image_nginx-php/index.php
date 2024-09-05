    <?php
    // Obtener la hora actual en el formato deseado
    $hora_actual = date("Y-m-d H:i:s");
    
    // Obtener el hostname del servidor
    $hostname = gethostname();
    
    // Imprimir la información directamente en el HTML
    echo "<h1>Test Web Page!</h1>";
    echo "<p>Hora actual: " . $hora_actual . "</p>";
    echo "<p>Hostname: " . $hostname . "</p>";
    echo "<p>IP: " . $_SERVER['SERVER_ADDR'] . "</p>";
    ?>
