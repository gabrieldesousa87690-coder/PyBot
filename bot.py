import asyncio, os, json, importlib, time, random
from fbchat_muqit import Client, ThreadType

# Carrega as configs
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Carrega os cookies raiz
with open('cookies.json', 'r', encoding='utf-8') as f:
    cookies = json.load(f)

# ==========================================
# SISTEMA DE CARREGAMENTO DE COMANDOS E EVENTOS
# ==========================================

def carregar_comandos():
    """Carrega todos os arquivos .py dentro de /scripts/cmds"""
    comandos = {}
    cmds_path = os.path.join(os.getcwd(), "scripts", "cmds")
    
    if os.path.exists(cmds_path):
        for filename in os.listdir(cmds_path):
            if filename.endswith(".py"):
                nome_modulo = filename[:-3]
                spec = importlib.util.spec_from_file_location(f"cmd_{nome_modulo}", os.path.join(cmds_path, filename))
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo)
                if hasattr(modulo, "cmd") and hasattr(modulo, "name"):  # Espera um objeto 'cmd'
                    comandos[modulo.name] = modulo.cmd
                    print(f"✅ Comando carregado: {modulo.name}")
    return comandos

def carregar_eventos():
    """Carrega todos os arquivos .py dentro de /scripts/events"""
    eventos = []
    events_path = os.path.join(os.getcwd(), "scripts", "events")
    
    if os.path.exists(events_path):
        for filename in os.listdir(events_path):
            if filename.endswith(".py"):
                nome_modulo = filename[:-3]
                spec = importlib.util.spec_from_file_location(f"evt_{nome_modulo}", os.path.join(events_path, filename))
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo)
                if hasattr(modulo, "event"):  # Espera uma função 'event'
                    eventos.append(modulo.event)
                    print(f"✅ Evento carregado: {nome_modulo}")
    return eventos

comandos = carregar_comandos()
eventos = carregar_eventos()

# ==========================================
# LÓGICA DO BOT (O CORAÇÃO)
# ==========================================

async def handler(message_object, thread_id, thread_type, author_id):
    """Função chamada a cada nova mensagem"""
    
    # 1. Verifica se é evento (roda antes de tudo)
    for evento in eventos:
        try:
            await evento(message_object, thread_id, thread_type)
        except Exception as e:
            print(f"Erro no evento: {e}")
    
    # 2. Verifica Blacklist
    if str(author_id) in config["blacklist"]:
        return
    
    # 3. Ignora mensagens sem prefixo ou do próprio bot
    if not message_object.text or message_object.text.startswith(config["prefix"]) is False:
        return
    
    # 4. Extrai comando e argumentos
    cmd_split = message_object.text.split(" ")
    cmd_name = cmd_split[0][1:].lower()  # Remove o prefixo
    
    if cmd_name in comandos:
        # Verifica permissão (Dono ou Whitelist)
        if str(author_id) in config["ownerUids"] or str(author_id) in config["whitelist"]:
            cmd_func = comandos[cmd_name]
            try:
                # Pausa aleatória para parecer humano
                await asyncio.sleep(random.uniform(1.5, 3.5))
                await cmd_func(message_object, thread_id, thread_type, config)
            except Exception as e:
                print(f"Erro no comando {cmd_name}: {e}")
                await client.sendMessage("❌ Erro interno no comando.", thread_id, thread_type)
        else:
            await client.sendMessage("⛔ Você não tem permissão, mané.", thread_id, thread_type)

async def main():
    client = Client(cookies=cookies)
    print("🤖 Bot iniciado e raiz! Logado com sucesso.")
    
    @client.on("message")
    async def on_message(message_object):
        if not message_object.is_unsent: # Ignora mensagens apagadas
            author_id = message_object.author.id
            thread_id = message_object.thread.id
            thread_type = message_object.thread.type
            await handler(message_object, thread_id, thread_type, author_id)
    
    # Mantém o bot rodando para sempre (com sleeps humanos)
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
