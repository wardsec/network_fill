from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading
import socket
import time
import os

# Instanciação do objeto Flask para a criação do servidor web.
app = Flask(__name__)

# Carregando variáveis de ambiente a partir do arquivo .env.

PORT = 5555

HOST = '0.0.0.0'

# Dicionário para armazenar informações dos agentes conectados.
agents = {}

# Criando um socket para aceitar conexões dos agentes.
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()


def log_activity(activity):
    """
    Função para logar atividades do servidor, armazenando-as em um arquivo de texto.

    Args:
    activity (str): A atividade a ser logada.
    """
    with open("server_log.txt", "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {activity}\n")


def handle_client(conn, addr):
    """
    Função para lidar com a conexão de novos agentes.
    Ela solicita o nome do agente e armazena informações sobre a conexão.

    Args:
    conn (socket.socket): O objeto de socket representando a conexão com o agente.
    addr (tuple): O endereço IP e a porta do agente.
    """
    conn.sendall("GET_NAME".encode())
    agent_name = conn.recv(1024).decode('utf-8')
    agents[agent_name] = {"connection": conn, "last_msg_time": time.time(), "status": "online"}
    log_activity(f"Conexão estabelecida com {agent_name} em {addr}")


def check_agent_status(agent_name, connection):
    """
    Função para verificar se um agente está online, enviando um "PING" e esperando por um "PONG".

    Args:
    agent_name (str): O nome do agente.
    connection (socket.socket): O objeto de socket representando a conexão com o agente.

    Returns:
    bool: Retorna True se o agente está online, False caso contrário.
    """
    try:
        connection.sendall("PING".encode())
        connection.settimeout(5)
        response = connection.recv(1024).decode()
        connection.settimeout(None)
        return response == "PONG"
    except socket.timeout:
        print(f"Timeout while checking the status of agent {agent_name}")
    except Exception as e:
        print(f"Error while checking the status of agent {agent_name}: {e}")
    return False


def update_agent_statuses():
    """
    Função executada em um thread separado para atualizar periodicamente o status dos agentes.
    """
    while True:
        for agent_name, data in list(agents.items()):
            connection = data.get("connection")
            if connection:
                is_online = check_agent_status(agent_name, connection)
                agents[agent_name]["status"] = "online" if is_online else "offline"
        time.sleep(5)


# Iniciando o thread para atualização dos status dos agentes.
status_updater_thread = threading.Thread(target=update_agent_statuses, daemon=True)
status_updater_thread.start()


def accept_connections():
    """
    Função para aceitar conexões de agentes e criar um novo thread para cada agente.
    """
    while True:
        conn, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr))
        client_thread.start()


# Rota principal que renderiza a página inicial com a lista de agentes e seus status.
@app.route('/')
def index():
    return render_template('index.html', agents={name: data["status"] for name, data in agents.items()})


# Rota para enviar um comando a um agente específico e receber a resposta.
@app.route('/send_command', methods=['POST'])
def send_command():
    agent_name = request.form.get('agent_name')
    command = request.form.get('command')
    response = "Erro: Agente não encontrado."

    if agent_name in agents:
        connection = agents[agent_name]["connection"]
        connection.sendall(command.encode())
        response = connection.recv(1024).decode('utf-8')
        log_activity(f"Resposta de {agent_name}: {response}")

    return jsonify(result=response)


# Rota para enviar um comando a todos os agentes online e logar as respostas.
@app.route('/send_command_to_all', methods=['POST'])
def send_command_to_all():
    command = request.form.get('command')
    responses = {}
    for agent_name, data in agents.items():
        if data["status"] == "online":
            try:
                data["connection"].sendall(command.encode())
                response = data["connection"].recv(1024).decode('utf-8')
                responses[agent_name] = response
            except Exception as e:
                responses[agent_name] = str(e)
    for agent_name, response in responses.items():
        log_activity(f"Resposta de {agent_name}: {response}")

    # Return all responses
    return jsonify(result=responses)



# Iniciando o servidor Flask e o thread para aceitar conexões.
if __name__ == "__main__":
    threading.Thread(target=accept_connections).start()
    app.run(host='0.0.0.0', port=5000)
