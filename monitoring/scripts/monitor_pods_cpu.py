import subprocess
import re
import mysql.connector

# Configuración de la base de datos
db_config = {
    'host': 'mysql',
    'database': 'metrics',
    'user': 'monitor',
    'password': 'hola1234'
}

# Datos para acceso a recursos de cluster
token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
metrics_url = "https://192.168.49.2:10250/metrics/resource"
server = 'https://192.168.49.2:8443'


# Funcion para obtener metricas
def get_kubernetes_metrics(token):

    command = [
        "curl", "-k", 
        "-H", f"Authorization: Bearer {token}", 
        metrics_url
    ]
    
    # Ejecuto consulta
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode == 0:
        return result.stdout
    else:
        print(f"Error al ejecutar curl: {result.stderr}")
        return None


def parse_metrics(metrics_output):
    # Esta regex está basada en la estructura esperada de las métricas
    pattern = re.compile(r'pod_cpu_usage_seconds_total{namespace="([^"]+)",pod="([^"]+)"} ([\d\.]+)')
    
    records = []

    for match in pattern.finditer(metrics_output):
        namespace, pod, cpu_usage = match.groups()
        records.append({
            "namespace": namespace,
            "pod": pod,
            "cpu_usage_seconds": float(cpu_usage)
        })

    return records


def store_data_in_db(records):
    # Conexión con base de datos
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    
    # Creacion de tabla en caso de que no exista
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cpu_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pod_id CHAR(64),
        namespace VARCHAR(255),
        pod VARCHAR(255),
        cpu_usage_seconds DOUBLE,
        UNIQUE(pod_id)
    )
    """)

    # Creacion de tabla para control de namespaces
    cur.execute("""
    CREATE TABLE IF NOT EXISTS namespaces_cpu (
        id INT AUTO_INCREMENT PRIMARY KEY,
        namespace VARCHAR(255) UNIQUE,
        cpu_time_actual_pods DOUBLE default 0,
        cpu_time_terminated_pods DOUBLE default 0,
        cpu_time_total DOUBLE AS (cpu_time_actual_pods + cpu_time_terminated_pods) STORED,
        cpu_quota DOUBLE default 100
    )
    """)
    
    existing_pods = set()
    
    # Inserción de los registros
    for record in records:

        # No se tienen en cuenta PODs del sistema
        if record['namespace'] == 'kube-system' or record['namespace'] == 'default' or record['namespace'] == 'monitoring':
            continue
        
        # Obtencion de Pod ID para hacer el registro
        pod_id = get_pod_id(record['namespace'], record['pod'], token)
        existing_pods.add(pod_id)
        
        # Insercion en DB
        cur.execute("""
        INSERT INTO cpu_metrics (pod_id, namespace, pod, cpu_usage_seconds)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            namespace = VALUES(namespace),
            pod = VALUES(pod),
            cpu_usage_seconds = VALUES(cpu_usage_seconds)
        """, (pod_id, record['namespace'], record['pod'], record['cpu_usage_seconds']))
        
        # Insertar informacion de namespace en namespaces_cpu si no existe
        cur.execute("""
        INSERT IGNORE INTO namespaces_cpu (namespace)
        VALUES (%s)
        """, (record['namespace'],))
        
        
    # Obtener todos los pods registrados en la base de datos
    cur.execute("SELECT pod_id, namespace, pod, cpu_usage_seconds FROM cpu_metrics")
    db_pods = cur.fetchall()
    
    # Resetear contadores de tiempo actual de pods
    cur.execute("UPDATE namespaces_cpu SET cpu_time_actual_pods = 0")

    for db_pod in db_pods:
        db_pod_id, db_namespace, db_pod_name, db_cpu_usage = db_pod
        
        if db_pod_id not in existing_pods:
            # Acumulo cpu de pod eliminado
            cur.execute("""
            UPDATE namespaces_cpu
            SET cpu_time_terminated_pods = cpu_time_terminated_pods + %s
            WHERE namespace = %s
            """, (db_cpu_usage, db_namespace))
            
            # Pod no encontrado en la lista de pods actuales por lo que el pod ya no existe, se elimina de db
            cur.execute("DELETE FROM cpu_metrics WHERE pod_id = %s", (db_pod_id,))
            print("Deleted pod:", db_pod_id)
        else:
            # Acumulo cpu de pods vivos
            cur.execute("""
            UPDATE namespaces_cpu
            SET cpu_time_actual_pods = cpu_time_actual_pods + %s
            WHERE namespace = %s
            """, (db_cpu_usage, db_namespace))
    
    conn.commit()
    cur.close()
    conn.close()


def get_pod_id(namespace, pod_name, token):
    # Construir el comando kubectl
    command = f"kubectl describe pods --token={token} -s {server} --insecure-skip-tls-verify -n {namespace} {pod_name} | grep 'Container ID'"
    
    # Ejecutar el comando y capturar la salida
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    # Buscar el pod_id en la salida del comando
    for line in result.stdout.splitlines():
        if 'Container ID' in line:
            return line.split("docker://")[1].strip()
    
    return None



if __name__ == '__main__':
    
    # Se obtiene token para poder hacer consultas al cluster
    with open(token_path, 'r') as file:
        token = file.read().strip()
        
    # Ejecuta la consulta y almacena los datos
    metrics_output = get_kubernetes_metrics(token)
    print("Metricas:", metrics_output)
    
    # Si se obtuvieron metricas
    if metrics_output:
        records = parse_metrics(metrics_output)
        print("Records:", records)
        store_data_in_db(records)

