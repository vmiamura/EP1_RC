import socket 
import threading

# Variável global para sinalizar o encerramento da conexão.
# Usada para interromper o loop principal e a thread de recebimento de mensagens.
encerrar_conexao = False  

def criar_socket():
    """
    Cria um socket TCP/IP usando o protocolo IPv4.

    Returns:
        socket.socket: Um novo objeto socket configurado para IPv4 e TCP.
    """
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def conectar_servidor(cliente_socket, host, port):
    """
    Estabelece conexão com o servidor especificado.

    Args:
        cliente_socket (socket.socket): O socket do cliente.
        host (str): O endereço do servidor.
        port (int): A porta do servidor.

    Raises:
        Exception: Qualquer exceção que ocorra ao tentar conectar.
    """
    try:
        cliente_socket.connect((host, port))
        print("Conectado ao servidor de adivinhação.")
    except Exception as e:
        print(f"Erro ao conectar ao servidor: {e}")
        raise e  # Lança a exceção para ser tratada pelo chamador.

def receber_mensagens(cliente_socket):
    """
    Thread responsável por receber mensagens do servidor.

    Args:
        cliente_socket (socket.socket): O socket do cliente.
    """
    global encerrar_conexao
    while not encerrar_conexao:
        try:
            resposta = cliente_socket.recv(1024).decode()
            if not resposta or resposta.upper() == "/DESCONECTAR":
                # Verifica se o servidor solicitou desconexão.
                print("Servidor solicitou desconexão.")
                encerrar_conexao = True  # Sinaliza para encerrar o loop no cliente.
                break
            print(f"Servidor: {resposta}")  # Exibe a mensagem recebida do servidor.
        except ConnectionResetError:
            # Caso a conexão seja encerrada abruptamente pelo servidor.
            print("Conexão com o servidor encerrada.")
            encerrar_conexao = True
            break
        except Exception as e:
            if not encerrar_conexao:
                print(f"Erro ao receber mensagem: {e}")
            break

def iniciar_thread_recebimento(cliente_socket):
    """
    Inicia uma thread para receber mensagens do servidor.

    Args:
        cliente_socket (socket.socket): O socket do cliente.

    Returns:
        threading.Thread: A thread que está recebendo mensagens.
    """
    thread_receber = threading.Thread(target=receber_mensagens, args=(cliente_socket,))
    thread_receber.start()
    return thread_receber

def enviar_mensagens(cliente_socket):
    """
    Loop principal que envia mensagens digitadas pelo usuário ao servidor.

    Args:
        cliente_socket (socket.socket): O socket do cliente.
    """
    global encerrar_conexao
    while not encerrar_conexao:
        mensagem = input()  # Aguarda a mensagem do usuário.
        if mensagem.upper() == "/DESCONECTAR":
            # O usuário solicitou desconexão.
            encerrar_conexao = True  # Sinaliza para encerrar a conexão.
            cliente_socket.sendall(mensagem.encode())  # Envia o comando de desconexão ao servidor.
            break
        cliente_socket.sendall(mensagem.encode())  # Envia a mensagem ao servidor.

def fechar_socket(cliente_socket):
    """
    Fecha o socket do cliente de maneira segura.

    Args:
        cliente_socket (socket.socket): O socket do cliente.
    """
    global encerrar_conexao
    encerrar_conexao = True  # Garante que o loop e a thread sejam finalizados.
    try:
        cliente_socket.shutdown(socket.SHUT_RDWR)  # Encerra a leitura e escrita do socket.
    except Exception as e:
        print(f"Erro ao tentar encerrar o socket: {e}")
    finally:
        cliente_socket.close()  # Fecha o socket.

def start_client(host='localhost', port=12345):
    """
    Função principal que inicia o cliente, conecta ao servidor e gerencia as threads de envio e recebimento.

    Args:
        host (str, optional): Endereço do servidor. Padrão é 'localhost'.
        port (int, optional): Porta do servidor. Padrão é 12345.
    """
    cliente_socket = criar_socket()  # Cria o socket do cliente.
    try:
        conectar_servidor(cliente_socket, host, port)  # Conecta ao servidor.

        # Inicia a thread de recebimento de mensagens.
        thread_receber = iniciar_thread_recebimento(cliente_socket)

        # Inicia o envio de mensagens.
        enviar_mensagens(cliente_socket)

        # Espera a thread de recebimento terminar.
        thread_receber.join()

    except KeyboardInterrupt:
        # Trata interrupções do teclado (Ctrl+C).
        print("\nFechando conexão.")
        encerrar_conexao = True
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        fechar_socket(cliente_socket)  # Garante que o socket seja fechado no final.
        print("Conexão encerrada.")

if __name__ == "__main__":
    start_client()  # Inicia o cliente.