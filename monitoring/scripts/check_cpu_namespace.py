import subprocess
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
server = 'https://192.168.49.2:8443'

def check_cpu_time_usage(token):
    
    # Conexión con base de datos
    conn = mysql.connector.connect(**db_config)
    cur = conn.cursor()
    
    # Consulta para obtener namespaces, cuotas y tiempos totales de CPU
    cur.execute("SELECT namespace, cpu_time_total, cpu_quota FROM namespaces_cpu")
    namespaces = cur.fetchall()

    for namespace_data in namespaces:
        namespace = namespace_data[0]
        cpu_time_total = namespace_data[1]
        cpu_quota = namespace_data[2]
        
        if cpu_time_total > cpu_quota:
            # Si se supero la quota bajo cantidad de pods disponibles a cero para que no se puedan crear mas            
            command_apply = f"kubectl apply -f /scripts/pod-quota-to-zero.yaml --token={token} -s {server} --insecure-skip-tls-verify -n {namespace}"
            result_apply = subprocess.run(command_apply, shell=True, capture_output=True, text=True)
            
            print("Kubectl apply:", result_apply.stdout)
                                    
            command_get = f"kubectl get pods --token={token} -s {server} --insecure-skip-tls-verify -n {namespace}"
            result_get = subprocess.run(command_get, shell=True, capture_output=True, text=True)
            print("Kubectl get:", result_get.stdout)
            
            for line in result_get.stdout.strip().split("\n")[1:]:
                fields = line.split()
                pod_name= fields[0]
                                
                # Elimino los pods que están corriendo
                command_delete = f"kubectl delete pod {pod_name} --token={token} -s {server} --insecure-skip-tls-verify -n {namespace}"
                result_delete = subprocess.run(command_delete, shell=True, capture_output=True, text=True)
                print("Kubectl delete:", result_delete)

    conn.commit()
    cur.close()
    conn.close()




if __name__ == '__main__':

    # Se obtiene token para poder hacer consultas al cluster
    with open(token_path, 'r') as file:
        token = file.read().strip()
    
    check_cpu_time_usage(token)