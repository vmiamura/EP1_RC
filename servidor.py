import socket
import threading
import random

# Dicionário global para armazenar os jogadores conectados e seus dados.
# Chave: nome do jogador, Valor: objeto ClientHandler associado ao jogador.
jogadores = {}

# Variável global para indicar se o jogo está em andamento.
jogo_comecou = False

# Variável global que armazena o número a ser adivinhado.
numero_para_adivinhar = 0

# Lock global para controlar o acesso aos recursos compartilhados entre threads.
lock = threading.Lock()

class ClientHandler(threading.Thread):
    """
    Classe que lida com cada cliente conectado ao servidor em uma thread separada.

    Atributos:
        conn (socket.socket): Conexão com o cliente.
        addr (tuple): Endereço do cliente (host, porta).
        nome (str): Nome do jogador.
        score (int): Pontuação atual do jogador.
    """
    def __init__(self, conn, addr):
        threading.Thread.__init__(self)
        self.conn = conn  # Conexão socket com o cliente.
        self.addr = addr  # Endereço (IP, porta) do cliente.
        self.nome = None  # Nome do jogador (será solicitado ao conectar).
        self.score = 0  # Pontuação inicial do jogador.

    def run(self):
        """
        Método principal da thread que é executado ao iniciar a conexão do cliente.
        Responsável por interagir com o cliente, recebendo e enviando mensagens.
        """
        global jogadores
        print(f"Conectado com {self.addr}")
        with self.conn:
            # Solicita o nome de usuário ao conectar.
            self.enviar("Digite seu nome de usuário: ")
            nome = self.conn.recv(1024).decode()

            # Verifica se o nome de usuário já está em uso.
            with lock:
                if nome in jogadores:
                    # Nome já em uso, envia mensagem de erro e encerra a conexão.
                    self.enviar("Nome de usuário já em uso.")
                    print(f"Conexão encerrada. Tentativa de conexão com nome de usuário já em uso: {nome} de {self.addr}")
                    self.conn.close()
                    return
                else:
                    # Nome válido, adiciona o jogador à lista.
                    self.nome = nome  # Atribui o nome ao jogador.
                    jogadores[nome] = self  # Adiciona o jogador ao dicionário global.
                    self.anunciar(f"{nome} entrou no jogo!")  # Notifica todos os jogadores.
                    self.enviar(f"Bem-vindo, {nome}!\nComandos: /START, /SCORE, /END ou /DESCONECTAR")
                    print(f"Jogador {nome} conectado de {self.addr}")

            try:
                while True:
                    # Recebe a mensagem do cliente.
                    mensagem = self.conn.recv(1024).decode().strip()

                    # Verifica se o cliente deseja desconectar.
                    if mensagem.upper() == "/DESCONECTAR":
                        self.enviar("/DESCONECTAR")  # Envia comando de desconexão para o cliente.
                        self.remove_jogador()  # Remove o jogador da lista global.
                        break  # Sai do loop e encerra a thread.
                    elif mensagem.startswith("/"):
                        # Processa comandos especiais iniciados com '/'.
                        self.processa_comando(mensagem.upper())
                    else:
                        # Processa tentativas de adivinhação (mensagens que não são comandos).
                        self.processar_adivinhacao(mensagem)
            except ConnectionError:
                # Trata erros de conexão, como cliente desconectado abruptamente.
                print(f"Cliente {self.addr} desconectou.")
            except Exception as e:
                print(f"Erro ao lidar com o cliente: {e}")
            finally:
                try:
                    self.remove_jogador()  # Remove o jogador da lista global, se ainda estiver presente.
                    self.conn.shutdown(socket.SHUT_RDWR)  # Fecha a conexão de maneira segura.
                except Exception as e:
                    print(f"Erro ao encerrar conexão com {self.addr}: {e}")
                finally:
                    self.conn.close()  # Fecha o socket do cliente.
                    print(f"Conexão com {self.addr} encerrada.")

    def enviar(self, mensagem):
        """
        Envia uma mensagem para o cliente.

        Args:
            mensagem (str): Mensagem a ser enviada.
        """
        try:
            self.conn.send(mensagem.encode())  # Envia a mensagem codificada para o cliente.
        except Exception as e:
            print(f"Erro ao enviar mensagem para {self.nome}: {str(e)}")
            self.conn.close()

    def remove_jogador(self):
        """
        Remove o jogador da lista global de jogadores.
        """
        global jogadores
        with lock:
            if self.nome in jogadores:
                del jogadores[self.nome]  # Remove o jogador do dicionário.
                self.anunciar(f"{self.nome} saiu do jogo.")  # Notifica os demais jogadores.

    def processa_comando(self, comando):
        """
        Processa os comandos enviados pelos jogadores.

        Args:
            comando (str): Comando recebido do jogador.
        """
        if comando == "/START":
            self.inicia_jogo()  # Inicia um novo jogo.
        elif comando == "/SCORE":
            str_rank = self.ranking()  # Obtém o ranking dos jogadores.
            self.enviar(str_rank)  # Envia o ranking para o jogador.
        elif comando == "/END":
            self.finalizar_jogo()  # Finaliza o jogo em andamento.
            self.zerar_scores()  # Zera as pontuações de todos os jogadores.
            self.enviar("Comandos: /START, /SCORE, /END ou /DESCONECTAR")
        else:
            self.enviar("Comando inválido!\nComandos: /START, /SCORE, /END ou /DESCONECTAR")

    def inicia_jogo(self):
        """
        Inicia um novo jogo, gerando um número aleatório a ser adivinhado.
        """
        global jogo_comecou, numero_para_adivinhar
        with lock:
            if jogo_comecou:
                self.enviar("Jogo já iniciado!")  # Informa que já existe um jogo em andamento.
                return
            numero_para_adivinhar = random.randint(1, 100)  # Gera um número aleatório entre 1 e 100.
            jogo_comecou = True  # Marca que o jogo começou.
            print(f"Novo número gerado: {numero_para_adivinhar}")
            self.anunciar(f"Novo jogo iniciado! Tente adivinhar o número entre 1 e 100.")  # Notifica todos os jogadores.

    def anunciar(self, mensagem):
        """
        Envia uma mensagem para todos os jogadores conectados.

        Args:
            mensagem (str): Mensagem a ser anunciada.
        """
        global jogadores
        with lock:
            for cliente in jogadores.values():
                cliente.enviar(mensagem)

    def ranking(self):
        """
        Retorna o ranking dos jogadores com base nas suas pontuações.

        Returns:
            str: Uma string formatada com o ranking dos jogadores.
        """
        global jogadores
        with lock:
            # Ordena os jogadores pela pontuação (score) em ordem decrescente.
            ranking = sorted(jogadores.values(), key=lambda jogador: jogador.score, reverse=True)
            mensagem = "Ranking:\n"
            posicao = 1
            for jogador in ranking:
                mensagem += f"{posicao}. {jogador.nome}: {jogador.score}\n"
                posicao += 1
            return mensagem

    def finalizar_jogo(self):
        """
        Finaliza o jogo em andamento e anuncia o ranking.
        """
        global jogo_comecou
        with lock:
            if not jogo_comecou:
                self.enviar("Nenhum jogo em andamento para finalizar.")  # Informa que não há jogo ativo.
                return
            self.anunciar(f"Jogo finalizado por: {self.nome}!")  # Notifica que o jogo foi finalizado.
            jogo_comecou = False  # Marca que o jogo foi encerrado.
            str_rank = self.ranking()  # Obtém o ranking.
            self.anunciar(str_rank)  # Anuncia o ranking para todos os jogadores.

    def zerar_scores(self):
        """
        Zera as pontuações de todos os jogadores.
        """
        global jogadores
        with lock:
            for jogador in jogadores.values():
                jogador.score = 0  # Reseta a pontuação do jogador.

    def processar_adivinhacao(self, opcao):
        """
        Processa a tentativa de adivinhação do jogador.

        Args:
            opcao (str): A tentativa de adivinhação do jogador (deve ser um número).
        """
        global numero_para_adivinhar, jogo_comecou
        try:
            opcao = int(opcao)  # Converte a entrada em número inteiro.
            if not jogo_comecou:
                self.enviar("Nenhum jogo em andamento. Utilize /START ou aguarde alguém iniciar o jogo.")  # Informa que não há jogo ativo.
            elif opcao == numero_para_adivinhar:
                # Jogador acertou o número.
                self.anunciar(f"{self.nome} acertou o número: {numero_para_adivinhar}!")  # Notifica todos os jogadores.
                self.score += 1  # Incrementa a pontuação do jogador.
                print(f"{self.nome} acertou o número: {numero_para_adivinhar}.")
                self.finalizar_jogo()  # Finaliza o jogo após o acerto.
                self.inicia_jogo()  # Inicia um novo jogo automaticamente.
            elif opcao < numero_para_adivinhar:
                self.enviar("O número é maior.")  # Dá uma dica ao jogador.
            else:
                self.enviar("O número é menor.")  # Dá uma dica ao jogador.
        except ValueError:
            # Trata entradas que não são números inteiros.
            self.enviar("Por favor, envie uma entrada válida (número inteiro).")

def start_server(host='localhost', port=12345):
    """
    Inicia o servidor e aguarda conexões dos clientes.

    Args:
        host (str, optional): Endereço do servidor. Padrão é 'localhost'.
        port (int, optional): Porta do servidor. Padrão é 12345.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))  # Liga o socket ao host e porta fornecidos.
        server_socket.listen()  # Coloca o socket em modo de escuta.
        print(f"Servidor iniciado em {host}: {port}.")
        print("Aguardando conexões...")

        # Aceita conexões de novos clientes indefinidamente.
        while True:
            client_socket, addr = server_socket.accept()  # Aceita uma nova conexão.
            client_handler = ClientHandler(client_socket, addr)  # Cria um novo manipulador de cliente.
            client_handler.start()  # Inicia a thread para lidar com o novo cliente.

if __name__ == "__main__":
    start_server()  # Inicia o servidor.