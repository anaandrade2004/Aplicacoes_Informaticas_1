import os
import re
import json
import threading
from datetime import datetime, timedelta
import time

# Carregar base de dados
bd_file = open("bd.json", "r", encoding="utf-8")
bd = json.load(bd_file)
bd_file.close()

# Menus
menu_opcoes = """
===== MENU DO MÉDICO =====
1- Admissão de um novo utente
2- Ver utente existente
3- Atualizar base de dados
0- Sair
"""

menu_ver_utente = """
===== MENU DO MÉDICO =====
1- Novo exame
2- Alterar exame
3- Cancelar exame
4- Relatório de exames
5- Ver marcações
6- Atualizar base de dados
0- Sair
"""

menu_exames = """
1- Raio-X
2- TAC
3- Ecografia
4- Ressonância Magnética
5- Análises Clínicas
0- Sair
"""

# ----------------- Funções auxiliares --------------------
def obter_ultimo_numero_msg(pasta):    
    arquivos = [f for f in os.listdir(pasta + "/logs") if re.match(r"msg_(\d+)\.hl7", f)]
    if not arquivos:
        return 1
    
    numeros = [int(re.search(r"msg_(\d+)\.hl7", f).group(1)) for f in arquivos]
    return max(numeros) + 1

pasta_mirth = "./.mirth_data/medico"
n = obter_ultimo_numero_msg(pasta_mirth)

# ----------------- Funções HL7 --------------------
def criar_mensagem_hl7(msg_hl7, n):
    file_path = f"{pasta_mirth}/a_enviar/msg_{n}.hl7"
    with open(file_path, "w", encoding="utf-8") as f_out:
        f_out.write(msg_hl7)
    
    print(f"Mensagem HL7 gerada e guardada em: {file_path}")
    n += 1
    return n    

def criar_exame_hl7(paciente_id, tipo_msg, pedido_id, data_req):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    tipos = {
        "Raio-X": "RX",
        "TAC": "TAC",
        "Ecografia": "ECO",
        "Ressonância Magnética": "RM",
        "Análises Clínicas": "AC"
    }
    
    if tipo_msg not in tipos:
        print("Tipo de exame inválido.")
        return None
    
    codigo_exame = tipos[tipo_msg]
    
    msg = f"""MSH|^~\|PCE_SYSTEM|HOSPITAL_BRAGA|RIS_SYSTEM|RADIOLOGY_DEPT|{timestamp}||ORM^O01|{pedido_id}|P|2.5|||AL|
PID|||{paciente_id}||{bd[paciente_id]["apelido"].upper()}^{bd[paciente_id]["nome"].upper()}^^||{bd[paciente_id]["nascimento"]}|{bd[paciente_id]["sexo"].upper()}|
PV1||I|INT|||||||||||||||||
ORC|NW|{pedido_id}|{pedido_id}||||||{data_req}|
OBR|01|{pedido_id}|{pedido_id}|{codigo_exame}"""
    
    return msg

def alterar_hl7(paciente_id, pedido_id, data_req, tipo_msg):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    tipos = {
        "Raio-X": "RX",
        "TAC": "TAC",
        "Ecografia": "ECO",
        "Ressonância Magnética": "RM",
        "Análises Clínicas": "AC"
    }
    
    if tipo_msg not in tipos:
        print("Tipo de exame inválido.")
        return None
    
    codigo_exame = tipos[tipo_msg]
    
    msg = f"""MSH|^~\|PCE_SYSTEM|HOSPITAL_BRAGA|RIS_SYSTEM|RADIOLOGY_DEPT|{timestamp}||ORM^O01|{pedido_id}|P|2.5|||AL|
PID|||{paciente_id}||{bd[paciente_id]["apelido"].upper()}^{bd[paciente_id]["nome"].upper()}^^||{bd[paciente_id]["nascimento"]}|{bd[paciente_id]["sexo"].upper()}|
PV1||I|INT|||||||||||||||||
ORC|SC|{pedido_id}|{pedido_id}||||||{data_req}|
OBR|01|{pedido_id}|{pedido_id}|{codigo_exame}"""
    
    return msg

def cancelar_msg(pedido_id, paciente_id, msg_id):
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    msg = f"""MSH|^~\&|PCE_SYSTEM|HOSPITAL_BRAGA|RIS_SYSTEM|RADIOLOGY_DEPT|{timestamp}||ORM^O01|{msg_id}|P|2.5|||AL|
PID|||{paciente_id}||{bd[paciente_id]["apelido"].upper()}^{bd[paciente_id]["nome"].upper()}^^||{bd[paciente_id]["nascimento"]}|{bd[paciente_id]["sexo"].upper()}|
PV1||I|INT|||||||||||||||||
ORC|CA|{pedido_id}|{pedido_id}||||||{timestamp}|
OBR|01|{pedido_id}|{pedido_id}|{bd[paciente_id]["exame"][pedido_id]["tipo"]}"""
    return msg

# ----------------- Gestão de pacientes --------------------
def guardar_info(paciente_id, nome, apelido, nascimento, sexo):
    with open("bd.json", "w", encoding="utf-8") as f_out:
        if paciente_id not in bd:
            bd[paciente_id] = {
                "nome": nome.upper(),
                "apelido": apelido.upper(),
                "nascimento": nascimento.upper(),
                "sexo": sexo.upper(),
                "exame": {},
                "marcacoes": []
            }
        else:
            bd[paciente_id].update({
                "nome": nome.upper(),
                "apelido": apelido.upper(),
                "nascimento": nascimento,
                "sexo": sexo.upper()
            })
        
        json.dump(bd, f_out, indent=4, ensure_ascii=False)
        print("Informação guardada com sucesso!")

def criar_utente():
    paciente_id = input("ID do paciente: ")
    
    if paciente_id in bd:   ###################################################### adicionei a verificação do id na bd
        print(f"Erro: Já existe um utente com o ID '{paciente_id}'.")
        return
    
    nome = input("Nome: ")
    apelido = input("Apelido: ")
    nascimento = input("Data de nascimento (YYYY-MM-DD): ")
    sexo = input("Sexo (M/F): ")
    
    guardar_info(paciente_id, nome, apelido, nascimento, sexo)


# ----------------- Gestão de exames --------------------
def ver_exames_relatorios(paciente_id):
    if paciente_id not in bd:
        print("Paciente não encontrado.")
        return
    
    exames = bd[paciente_id].get("exame", {})
    
    if not exames:
        print("Não existem exames realizados.")
        return
    
    for exame_id, info_exame in exames.items():
        try:
            data_original = info_exame["data_realizacao"]
            data_formatada = datetime.strptime(data_original, "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M")
        except:
            data_formatada = "Data não disponível"
        
        print(f"""\n{'='*50}
Exame: {exame_id}
Data Realização: {data_formatada}
Tipo de Exame: {info_exame.get('tipo', 'Não especificado')}""")
        
        relatorio = info_exame.get('relatorio', {})
        if relatorio and 'texto' in relatorio and relatorio['texto'].strip():
            print(f"\nRelatório:\n{'-'*20}")
            print(relatorio['texto'].strip())
        else:
            print("\nRelatório: Não disponível")
    

def ver_marcacoes(paciente_id):
    if paciente_id not in bd:
        print("Paciente não encontrado.")
        return
    
    marcacoes = bd[paciente_id].get("marcacoes", [])
    
    if not marcacoes:
        print("Não existem marcações futuras.")
        return
    
    print("\nMarcações futuras:")
    for marcacao in marcacoes:
        try:
            data_original = marcacao["data"]
            data_formatada = datetime.strptime(data_original, "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M")
            print(f"ID: {marcacao['id']} | Tipo: {marcacao['tipo']} | Data: {data_formatada}")
        except:
            print(f"ID: {marcacao['id']} | Tipo: {marcacao['tipo']} | Data: Inválida")


                                 ###### ADICIONEI A VERIFICAÇÃO PARA NÃO HAVER MARCAÇÕES DO MESMO TIPO DE EXAME NA MESMA HORA, E TEM DE TER UM INTERVALO DE UMA HORA ANTES DA PRÓXIMA MARCAÇÃO
def novo_exame(paciente_id, n):
    print(menu_exames)
    tipo = input("Escolha o tipo de exame: ")

    tipos_validos = {
        "1": "Raio-X",
        "2": "TAC",
        "3": "Ecografia",
        "4": "Ressonância Magnética",
        "5": "Análises Clínicas"
    }

    if tipo not in tipos_validos:
        print("Opção inválida.")
        return n

    tipo_exame = tipos_validos[tipo]
    pedido_id = input("ID do pedido: ")

    while True:
        data_req = input("Data de realização (YYYYMMDDHHMM): ")
        try:
            data_exame = datetime.strptime(data_req, "%Y%m%d%H%M")
            data_atual = datetime.now()

            # Verificar se a data do exame é no futuro
            if data_exame <= data_atual:
                print("A data do exame deve ser futura. Por favor, insira uma data válida.")
                continue

            # Verificar se o exame pode ser marcado com base nas marcações já existentes para o tipo de exame
            conflito_encontrado = False
            for exame_id, info_exame in bd[paciente_id]["exame"].items():
                if info_exame["tipo"] == tipo_exame:
                    data_existente = datetime.strptime(info_exame["data_realizacao"], "%Y%m%d%H%M")
                    # Verificar se o novo exame está a menos de uma hora de qualquer outro exame do mesmo tipo
                    if abs((data_exame - data_existente).total_seconds()) < 3600:
                        print(f"Erro: Já existe um exame de {tipo_exame} marcado para esse horário ou em um intervalo de 1 hora.")
                        conflito_encontrado = True
                        break

            if conflito_encontrado:
                continue  # Volta para pedir novamente a data do exame

            break  # Se passou em todas as verificações, sai do loop

        except ValueError:
            print("Formato inválido. Tente novamente no formato YYYYMMDDHHMM.")

    # Adicionar à base de dados
    if paciente_id not in bd:
        bd[paciente_id] = {"exame": {}, "marcacoes": []}

    if "exame" not in bd[paciente_id]:
        bd[paciente_id]["exame"] = {}


    # Guardar na BD
    with open("bd.json", "w", encoding="utf-8") as f:
        json.dump(bd, f, indent=4, ensure_ascii=False)

    msg = criar_exame_hl7(paciente_id, tipo_exame, pedido_id, data_req)
    n = criar_mensagem_hl7(msg, n)
    print("Exame marcado com sucesso!")

    return n



def alterar_exame(paciente_id, n):
    exames = bd[paciente_id]["exame"]
    if not exames:
        print("Este paciente não tem exames marcados.")
        return n
    
    for exame_id, info_exame in exames.items():
        if info_exame.get("relatorio", {}) == {}:
            print(f"""Exame {exame_id}
Data de Realização - {info_exame["data_realizacao"]}
Tipo - {info_exame["tipo"]}
""")
    
    dsj = input("Deseja alterar algum exame? Se sim introduza o ID do exame: ")
    if dsj not in exames:
        print("ID de exame inválido!")
        return n
    
    data_str = exames[dsj]["data_realizacao"]
    data_exame = datetime.strptime(data_str, "%Y%m%d%H%M")
    data_atual = datetime.now()
    diferenca = data_exame - data_atual

    if diferenca < timedelta(days=1):
        print("Não é possível alterar: faltam menos de 24 horas para o exame.")
        return n
    
    out = input(f"""O que deseja alterar do exame {dsj}
1- Data de Realização
2- Tipo
0- Sair
""")
    
    if out == "1":
        while True:
            nova_data = input("Introduza a nova data de realização (YYYYMMDDHHMM): ")
            try:
                data_nova = datetime.strptime(nova_data, "%Y%m%d%H%M")
                if data_nova <= datetime.now():
                    print("A nova data deve ser futura. Tente novamente.")
                    continue
                break
            except ValueError:
                print("Formato inválido. Tente novamente no formato YYYYMMDDHHMM.")
        
        # Atualizar a marcação
        for marcacao in bd[paciente_id]["marcacoes"]:
            if marcacao["id"] == dsj:
                marcacao["data"] = nova_data
                break
        
        # Atualizar o exame
        exames[dsj]["data_realizacao"] = nova_data
        
        # Guardar na BD
        with open("bd.json", "w", encoding="utf-8") as f:
            json.dump(bd, f, indent=4, ensure_ascii=False)
        
        msg = alterar_hl7(paciente_id, dsj, nova_data, exames[dsj]["tipo"])
        n = criar_mensagem_hl7(msg, n)
        print("Data do exame alterada com sucesso!")
    
    elif out == "2":
        print(menu_exames)
        tipo = input("Escolha o novo tipo de exame: ")
        
        tipos_validos = {
            "1": "Raio-X",
            "2": "TAC",
            "3": "Ecografia",
            "4": "Ressonância Magnética",
            "5": "Análises Clínicas"
        }
        
        if tipo not in tipos_validos:
            print("Opção inválida.")
            return n
        
        novo_tipo = tipos_validos[tipo]
        
        # Atualizar a marcação
        for marcacao in bd[paciente_id]["marcacoes"]:
            if marcacao["id"] == dsj:
                marcacao["tipo"] = novo_tipo
                break
        
        # Atualizar o exame
        exames[dsj]["tipo"] = novo_tipo
        
        # Guardar na BD
        with open("bd.json", "w", encoding="utf-8") as f:
            json.dump(bd, f, indent=4, ensure_ascii=False)
        
        msg = alterar_hl7(paciente_id, dsj, exames[dsj]["data_realizacao"], novo_tipo)
        n = criar_mensagem_hl7(msg, n)
        print(f"Tipo de exame alterado para {novo_tipo}.")
    
    elif out == "0":
        print("A voltar para o menu anterior")
    
    return n

def cancelar_exame(paciente_id, n):
    exames = bd[paciente_id]["exame"]
    if not exames:
        print("Este paciente não tem exames marcados.")
        return n
    
    for exame_id, info_exame in exames.items():
        if info_exame.get("relatorio", {}) == {}:
            print(f"""Exame {exame_id}
Data de Realização - {info_exame["data_realizacao"]}
Tipo - {info_exame["tipo"]}
""")
    
    dsj = input("Deseja cancelar algum exame? Se sim introduza o ID do exame: ").strip()
    if dsj not in exames:
        print("ID de exame inválido!")
        return n
    
    data_str = exames[dsj]["data_realizacao"]
    data_exame = datetime.strptime(data_str, "%Y%m%d%H%M")
    data_atual = datetime.now()
    diferenca = data_exame - data_atual

    if diferenca < timedelta(days=1):
        print("Não é possível cancelar: faltam menos de 24 horas para o exame.")
        return n
    
    print("Cancelamento em processamento...")
    msg = cancelar_msg(dsj, paciente_id, n)
    n = criar_mensagem_hl7(msg, n)
    
    # Remover da lista de marcações
    
    
    # Manter no histórico de exames (apenas marcamos como cancelado)
    exames[dsj]["cancelado"] = True
    
    # Guardar na BD
    with open("bd.json", "w", encoding="utf-8") as f:
        json.dump(bd, f, indent=4, ensure_ascii=False)
    
    print(f"Exame {dsj} cancelado com sucesso!")
    return n

# ----------------- Monitorização de relatórios --------------------
def monitorar_relatorios(source_folder=".mirth_data/medico/recebido", intervalo=5):
    def processar_mensagem(caminho_arquivo):
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                mensagem_hl7 = f.read()
            
            linhas = [linha.strip() for linha in mensagem_hl7.split('\n') if linha.strip()]
            dados = {
                'paciente_id': None,
                'pedido_id': None,
                'descricao': '',
                'relatorio': []
            }
            
            coletar_relatorio = True
            
            for linha in linhas:
                segments = linha.split('|')
                if segments[0] == 'PID' and len(segments) > 3:
                    dados['paciente_id'] = segments[3].strip()
                elif segments[0] == 'ORC' and len(segments) > 2:
                    dados['pedido_id'] = segments[2].strip()
                elif segments[0] == 'OBR' and len(segments) > 4:
                    dados['descricao'] = segments[4].strip()
                elif coletar_relatorio and segments[0] == 'OBX' and len(segments) > 5 and segments[2] == 'TX':
                    texto = segments[5].strip()
                    if not texto:
                        coletar_relatorio = False
                    else:
                        dados['relatorio'].append(texto)
            
            if not dados['paciente_id'] or not dados['pedido_id']:
                print("Mensagem HL7 não contém ID do paciente ou pedido válido")
                return
            
            texto_relatorio = '\n'.join(dados['relatorio']) + '\n' if dados['relatorio'] else ''
            
            with open("bd.json", "r", encoding="utf-8") as f:
                bd = json.load(f)
            
            if (dados['paciente_id'] in bd and 
                'exame' in bd[dados['paciente_id']] and 
                dados['pedido_id'] in bd[dados['paciente_id']]['exame']):
                
                bd[dados['paciente_id']]['exame'][dados['pedido_id']]['relatorio'] = {
                    'descricao': dados['descricao'],
                    'texto': texto_relatorio,
                    'data_processamento': datetime.now().strftime("%Y%m%d%H%M%S")
                }
                
                # Remover da lista de marcações (já foi realizado)
                bd[dados['paciente_id']]["marcacoes"] = [
                    m for m in bd[dados['paciente_id']]["marcacoes"] 
                    if m["id"] != dados['pedido_id']
                ]
                
                with open("bd.json", "w", encoding="utf-8") as f:
                    json.dump(bd, f, indent=4, ensure_ascii=False)
                
                print(f"Relatório atualizado para exame {dados['pedido_id']} do paciente {dados['paciente_id']}")
            else:
                print(f"Paciente ou exame não encontrado na BD")
        
        except Exception as e:
            print(f"Erro ao processar {caminho_arquivo}: {str(e)}")
        finally:
            try:
                os.remove(caminho_arquivo)
            except:
                pass
            
    def loop_monitoramento():
        while True:
            try:
                arquivos = [f for f in os.listdir(source_folder) 
                          if f.endswith(".hl7") and f.startswith("msg_")]
                
                if arquivos:
                    arquivos.sort(key=lambda x: int(x[4:-4]))
                    for arquivo in arquivos:
                        caminho_arquivo = os.path.join(source_folder, arquivo)
                        processar_mensagem(caminho_arquivo)
                else:
                    time.sleep(intervalo)
            
            except Exception as e:
                print(f"Erro no loop de monitoramento: {str(e)}")
                time.sleep(intervalo)

    thread = threading.Thread(target=loop_monitoramento)
    thread.daemon = True
    thread.start()
    print(f"Monitorando relatórios HL7 na pasta {source_folder}...")
    return thread
def atualizar_base_dados():
    global bd
    with open("bd.json", "r", encoding="utf-8") as ficheiro:
        bd = json.load(ficheiro)
    print("Base de dados atualizada com sucesso.")

# ----------------- Programa principal --------------------
def run():
    n = 1
    monitorar_relatorios()
    
    while True:
        print(menu_opcoes)
        opcao = input("Escolha uma opção: ")
        
        if opcao == '1':
            print("\nAdmissão de um novo utente")
            criar_utente()
            
        elif opcao == '2':
            print("\nVer utente existente")
            paciente_id = input("ID do paciente: ")
            
            if paciente_id in bd:
                print(f"""Exibindo informações do paciente:
Nome: {bd[paciente_id]["nome"]}
Apelido: {bd[paciente_id]["apelido"]}
Género: {bd[paciente_id]["sexo"]}
Data de nascimento: {bd[paciente_id]["nascimento"]}
""")
                
                while True:
                    print(menu_ver_utente)
                    opcao_utente = input("Escolha uma opção: ")
                    
                    if opcao_utente == '1':
                        n = novo_exame(paciente_id, n)
                    elif opcao_utente == '2':
                        n = alterar_exame(paciente_id, n)
                    elif opcao_utente == '3':
                        n = cancelar_exame(paciente_id, n)
                    elif opcao_utente == '4':
                        ver_exames_relatorios(paciente_id)
                    elif opcao_utente == '5':
                        ver_marcacoes(paciente_id)
                    elif opcao_utente == '6':
                        atualizar_base_dados()
                    elif opcao_utente == '0':
                        print("A voltar para o menu principal")
                        break
            else:
                res = input(f"Paciente com ID {paciente_id} não encontrado. Deseja adicionar um novo utente? (s/n)")
                if res.lower() == 's':
                    criar_utente()
                else:
                    print("Operação cancelada.")
        elif opcao == '3':
            atualizar_base_dados()

        elif opcao == '0':
            print("Obrigado e volte sempre!")
            break
        
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    run()