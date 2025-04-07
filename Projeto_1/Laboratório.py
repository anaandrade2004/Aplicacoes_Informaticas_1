import os
import shutil
import uuid
from datetime import datetime, timedelta
import time
import threading
from collections import defaultdict
import json

# =============================================
# CONFIGURAÇÃO INICIAL E VARIÁVEIS GLOBAIS
# =============================================

# Carregar base de dados (bd.json)
bd_file = open("bd.json", "r", encoding="utf-8")
bd = json.load(bd_file)
bd_file.close()

# Dicionário para armazenar pedidos agendados
# Dicionário global para armazenar os exames agendados sem relatório
pedidos_agendados = {}

def listar_pedidos_agendados():
    global pedidos_agendados
    pedidos_agendados.clear()  # Limpa antes de preencher

    
    for paciente_id, dados in bd.items():
        for exame_id, exame_info in dados.get("exame", {}).items():
            if not exame_info["relatorio"]:
                # Adiciona o exame à lista de pedidos agendados
                pedidos_agendados[exame_id] = {
                    "nome": dados["nome"],
                    "apelido": dados["apelido"],
                    "paciente_id": paciente_id,
                    "tipo": exame_info["tipo"],
                    "data_realizacao": datetime.strptime(exame_info["data_realizacao"], "%Y%m%d%H%M")
                }
    

            

    if pedidos_agendados:
        for exame_id, dados in pedidos_agendados.items():
            print(f"- Paciente: {dados['nome']} {dados['apelido']} ({dados['paciente_id']})")
            print(f"  Exame: {exame_id}")
            print(f"  Tipo: {dados['tipo']}")
            print(f"  Data agendada: {dados['data_realizacao'].strftime('%Y-%m-%d %H:%M')}\n")
    else:
        print("Nenhum exame agendado sem relatório encontrado.")


# Pastas para processamento de arquivos
source_folder = ".mirth_data/relatórios/recebido"
dest_log_relatorios = ".mirth_data/relatórios/logs"
dest_send_folder = ".mirth_data/relatórios/a_enviar"

# =============================================
# FUNÇÕES DE MANIPULAÇÃO DE DADOS
# =============================================

def guardar_exame(id_exame, id_paciente, data_realzizacao, tipo, num_da_msg):
    file_path=f".mirth_data/relatórios/recebido/msg_{num_da_msg}.hl7" 
    bd[id_paciente]["exame"][id_exame]={"data_realizacao":data_realzizacao.upper(),"tipo":tipo.upper(),"relatorio":{}}
    bd[id_paciente]["marcacoes"].append({
        "id": id_exame,
        "tipo": tipo.upper(),
        "data": data_realzizacao.upper()
    })

    bd_file=open("bd.json", "w",encoding="utf-8")
    
    json.dump(bd,bd_file, indent=4, ensure_ascii=False)
    bd_file.close()
    
    print("Informação guardada com sucesso!")
    
    #eliminar msg após o processamento

    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Mensagem HL7 {file_path} eliminada com sucesso!")
    else:
        print(f"Aviso: O arquivo {file_path} não foi encontrado para exclusão.")



def process_hl7_message(file_path, dest_send_folder,menor):
    """Processa mensagens HL7 e executa ações conforme o tipo de mensagem"""
    with open(file_path, "r") as file:
        hl7_message = file.read()
    
    segmentos = hl7_message.strip().split("\n")
    dados = {}
    tipo_mensagem = None
    
    # Processar cada segmento da mensagem HL7
    for segmento in segmentos:
        campos = segmento.split("|")
       
        if campos[0] == "MSH":
            # Segmento MSH - Cabeçalho da mensagem
            dados["MSH"] = {
                "Separadores": campos[1],
                "Sistema_Envio": campos[2],
                "Local_Envio": campos[3],
                "Sistema_Recebimento": campos[4],
                "Local_Recebimento": campos[5],
                "DataHoraMensagem": campos[6],
                "Tipo_Mensagem": campos[8],
                "ID_Mensagem": campos[9],
                "Prioridade": campos[10],
                "Versao_HL7": campos[11],
            }
            tipo_msg = campos[8].split("^")[0]
                
        elif campos[0] == "PID":
            # Segmento PID - Informações do paciente
            id_paciente = campos[3].split("^^^")[0] if "^^^" in campos[3] else campos[3]
            nome_paciente = campos[5].split("^")
            dados["PID"] = {
                "Set_ID": campos[1],
                "Identificador_Paciente": id_paciente,
                "Nome_Paciente": nome_paciente[1] if len(nome_paciente) > 1 else "",
                "Sobrenome_Paciente": nome_paciente[0] if len(nome_paciente) > 0 else "",
                "Data_Nascimento": campos[7] if len(campos) > 7 else "",
                "Sexo": campos[8] if len(campos) > 8 else "",
            }
            
        elif campos[0] == "ORC":
            # Segmento ORC - Ordem comum
            dados["ORC"] = {
                "Tipo_Ordem": campos[1],
                "Numero_Ordem": campos[2],
                "DataHoraAgendamento": campos[9]
            }
            
            # Determinar tipo de mensagem baseado no segmento ORC
            if tipo_msg == "ORM":
                if dados["ORC"]["Tipo_Ordem"] == "NW":
                    tipo_mensagem = "REQ_EXAME"
                elif dados["ORC"]["Tipo_Ordem"] == "CA":
                    tipo_mensagem = "CANCELAMENTO"
                elif dados["ORC"]["Tipo_Ordem"] == "SC":
                    tipo_mensagem = "ALTERAÇÃO"

        elif campos[0] == "OBR":
            # Segmento OBR - Ordem de exame
            dados["OBR"] = {
                "Set_ID": campos[1],
                "Numero_Ordem": campos[2],
                "Codigo_Exame": campos[4] if len(campos) > 4 else "",
            }
            
        elif campos[0] == "PV1":
            # Segmento PV1 - Visita do paciente
            dados["PV1"] = {
                "Tipo_Atendimento": campos[2],
            }

    # Exibir informações extraídas
    print("\nDADOS EXTRAÍDOS:")
    print(f"Tipo de Mensagem: {tipo_mensagem}")
    print(f"Paciente: {dados['PID']['Sobrenome_Paciente']}, {dados['PID']['Nome_Paciente']}")
    print(f"ID: {dados['PID']['Identificador_Paciente']}")
    
    if "ORC" in dados:
        print(f"Ordem: {dados['ORC']['Numero_Ordem']} ({dados['ORC']['Tipo_Ordem']})")
    
    # Guardar informações do exame
    

    # Processar conforme o tipo de mensagem
    if tipo_mensagem == "REQ_EXAME":
        print("\nProcessando requisição de exame...")
        try:
            timestamp_pedido = datetime.strptime(dados['ORC']['DataHoraAgendamento'], "%Y%m%d%H%M")
            hora_relatorio = timestamp_pedido + timedelta(seconds=5)


            pedidos_agendados[dados['ORC']['Numero_Ordem']] = {
                'hora_agendada': hora_relatorio,
                'dados': dados
            }


            time.sleep(2)
            guardar_exame(
                dados['OBR']['Numero_Ordem'], 
                dados['PID']['Identificador_Paciente'], 
                dados['ORC']['DataHoraAgendamento'],
                dados["OBR"]["Codigo_Exame"],
                menor
            )

        except ValueError as e:
            print(f"Erro ao agendar (ValueError): {e}")
        except Exception as e:
            print(f"Erro inesperado: {e}")

            
    elif tipo_mensagem == "ALTERAÇÃO":
        print("Pedido a ser alterado. Aguarde ...")

        guardar_exame(
                        dados["OBR"]["Numero_Ordem"], 
                        id_paciente, 
                        dados["ORC"]["DataHoraAgendamento"], 
                        dados["OBR"]["Codigo_Exame"],
                        menor
                    )
    elif tipo_mensagem == "CANCELAMENTO":
        print(f"Exame {dados['ORC']['Numero_Ordem']} cancelado com sucesso!")
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Mensagem HL7 {file_path} eliminada com sucesso!")
        else:
            print(f"Aviso: O arquivo {file_path} não foi encontrado para exclusão.")
        file_path=f".mirth_data/relatórios/recebido/msg_{menor}.hl7" 
        dic_exames = bd[id_paciente]["exame"]
        exames = dic_exames.keys()

        if dados["ORC"]["Numero_Ordem"] in exames:
            del bd[id_paciente]["exame"][dados["ORC"]["Numero_Ordem"]]
            bd[id_paciente]["marcacoes"] = [m for m in bd[id_paciente]["marcacoes"] if m["id"] != dados["ORC"]["Numero_Ordem"]]

            with open("bd.json", "w", encoding="utf-8") as bd_file:
                json.dump(bd, bd_file, indent=4, ensure_ascii=False)

            

# =============================================
# FUNÇÕES DE LISTAGEM E ORDENAÇÃO
# =============================================

def obter_exames_ordenados(apenas_sem_relatorio=True):
    """Retorna lista de exames ordenados por data de realização"""
    exames = []
    
    for paciente_id, dados_paciente in bd.items():
        for exame_id, exame_info in dados_paciente.get("exame", {}).items():
            # Filtra por relatório se necessário
            if apenas_sem_relatorio and exame_info["relatorio"]:
                continue
                
            # Converte string de data para datetime
            try:
                data_exame = datetime.strptime(exame_info["data_realizacao"], "%Y%m%d%H%M")
            except ValueError:
                continue  # Ignora datas inválidas
                
            exames.append((
                data_exame,
                {
                    "paciente_id": paciente_id,
                    "exame_id": exame_id,
                    "nome": dados_paciente["nome"],
                    "apelido": dados_paciente["apelido"],
                    "tipo": exame_info["tipo"],
                    "relatorio": exame_info["relatorio"]
                }
            ))
    
    # Ordena por data mais próxima primeiro
    exames.sort(key=lambda x: x[0])
    return exames

def listar_pedidos_agendados():
    """Lista exames agendados sem relatório por ordem de data"""
    exames_ordenados = obter_exames_ordenados()
    
    if not exames_ordenados:
        print("\nNenhum exame agendado sem relatório encontrado.")
        return

    print("\n=== EXAMES AGENDADOS POR ORDEM DE REALIZAÇÃO ===")
    for data_exame, exame in exames_ordenados:
        print(f"\n- Data: {data_exame.strftime('%d/%m/%Y %H:%M')}")
        print(f"  Paciente: {exame['nome']} {exame['apelido']} ({exame['paciente_id']})")
        print(f"  Exame ID: {exame['exame_id']}")
        print(f"  Tipo: {exame['tipo']}")



# =============================================
# FUNÇÕES DE REALIZAÇÃO DE EXAME
# =============================================

def realizacao_exame():
    """Permite selecionar e gerar relatório para exames agendados"""
    exames_ordenados = obter_exames_ordenados()
    
    if not exames_ordenados:
        print("\nNenhum exame disponível para realização.")
        return

    print("\n=== EXAMES PARA REALIZAÇÃO ===")
    for idx, (data_exame, exame) in enumerate(exames_ordenados, 1):
        print(f"{idx}. {data_exame.strftime('%d/%m/%Y %H:%M')} | {exame['nome']} {exame['apelido']} | {exame['tipo']}")

    while True:
        try:
            escolha = input("\nEscolha o número do exame a realizar (ou 'exit' para cancelar): ")
            if escolha.lower() == 'exit':
                return
            escolha = int(escolha)
            if escolha == 0:
                return
            if 1 <= escolha <= len(exames_ordenados):
                exame_selecionado = exames_ordenados[escolha-1][1]
                break
            else:
                print("Número inválido. Tente novamente.")
        except ValueError:
            print("Entrada inválida. Digite um número ou 'exit'.")

    # Coletar dados do relatório
    print(f"\n=== EDITAR RELATÓRIO PARA EXAME {exame_selecionado['exame_id']} ===")
    print("Digite os campos do relatório (ou 'exit' a qualquer momento para finalizar e enviar)\n")
    
    campos_relatorio = {}
    for i in range(1, 15):
        if i == 1:
            padrao = exame_selecionado['tipo']
        elif i == 5:
            padrao = "RELATÓRIO:"
        else:
            padrao = ""
            
        campo = input(f"Campo OBX{i} ({padrao}): ") or padrao
        if campo.lower() == 'exit':
            break  # Sai do loop se usuário digitar exit
        campos_relatorio[f"OBX{i}"] = campo

    # Preencher campos restantes com vazio se usuário saiu antes
    for i in range(len(campos_relatorio) + 1, 15):
        campos_relatorio[f"OBX{i}"] = ""

    # Gerar mensagem HL7
    mensagem_hl7 = gerar_relatorio_agendado(
        paciente_id=exame_selecionado['paciente_id'],
        exame_id=exame_selecionado['exame_id'],
        campos_relatorio=campos_relatorio,
        dados_paciente=bd[exame_selecionado['paciente_id']]
    )

    print("\nRelatório gerado e enviado com sucesso!")

# =============================================
# FUNÇÃO DE GERAÇÃO DE RELATÓRIO ATUALIZADA
# =============================================

def gerar_relatorio_agendado(paciente_id, exame_id, campos_relatorio, dados_paciente):
    """Gera mensagem HL7 completa para o relatório"""
    data_hora = datetime.now().strftime("%Y%m%d%H%M%S")
    msg_id = str(uuid.uuid4())
    
    # Construir mensagem HL7
    hl7_content = [
        f"MSH|^~\&|PACS|HOSPITAL|SISTEMA|SISTEMA|{data_hora}||ORU^R01|{msg_id}|P|2.5",
        f"PID|||{paciente_id}||{dados_paciente['apelido']}^{dados_paciente['nome']}||{dados_paciente.get('data_nascimento', '')}|{dados_paciente.get('sexo', '')}",
        f"ORC|RE|{exame_id}|||CM||||{data_hora}",
        f"OBR|1|{exame_id}||{campos_relatorio['OBX1']}"
    ]

    # Adicionar campos OBX
    for idx in range(1, 15):
        hl7_content.append(
            f"OBX|{idx}|TX|||{campos_relatorio[f'OBX{idx}']}||||||F|||{data_hora}"
        )

    # Salvar arquivo HL7
    nome_arquivo = f"Relatório_{exame_id}.hl7"
    caminho_completo = os.path.join(dest_send_folder, nome_arquivo)
    
    with open(caminho_completo, 'w',encoding='utf-8') as f:
        f.write('\n'.join(hl7_content))
    
    return caminho_completo

def atualizar_base_dados():
    global bd
    with open("bd.json", "r", encoding="utf-8") as ficheiro:
        bd = json.load(ficheiro)
    print("Base de dados atualizada com sucesso.")


def mostrar_menu():
    while True:
        print("\n===== MENU DE LABORATORIAL =====")
        print("1. Listar exames agendados por ordem de realização")
        print("2. Realizar exame")
        print("3. Consultar base de dados completa")
        print("4. Atualizar base de dados")
        print("0. Sair")
        escolha = input("Escolha uma opção: ")

        if escolha == "1":
            listar_pedidos_agendados()
        elif escolha == "2":
            realizacao_exame()
        elif escolha == "3":
            
            print("\n=== Base de Dados ===")
            for paciente_id, info in bd.items():
                print(f"\nPaciente ID: {paciente_id}")
                exames = info.get("exame", {})
                for exame_id, exame_info in exames.items():
                    print(f"  Exame {exame_id}: {exame_info}")
        elif escolha == "4":
            atualizar_base_dados()
        elif escolha == "0":
            print("A encerrar o sistema...")
            os._exit(0)
        else:
            print("Opção inválida. Tente novamente.")

# =========================
# INÍCIO DO SISTEMA
# =========================
if __name__ == "__main__":
    listar_pedidos_agendados()
    

    # Iniciar thread de processamento de mensagens HL7
    def loop_mensagens():
        while True:
            arquivos = [f for f in os.listdir(source_folder) if f.endswith(".hl7")]
            if arquivos:
                numeros = [int(f.replace("msg_", "").replace(".hl7", "")) for f in arquivos]
                menor = min(numeros)
                arquivo_menor = f"msg_{menor}.hl7"
                print(f"\nA processar o {arquivo_menor}...")
                process_hl7_message(os.path.join(source_folder, arquivo_menor), dest_send_folder, menor)
            else:
                time.sleep(5)

    thread_processamento = threading.Thread(target=loop_mensagens)
    thread_processamento.daemon = True
    thread_processamento.start()

    # Mostrar menu principal
    mostrar_menu()
