import asyncio
import os
import json
import importlib
import time
import random
import sys
import subprocess
import datetime
from fbchat_muqit import Client, ThreadType

# ==========================================
# CARREGAMENTO DE CONFIG E COOKIES
# ==========================================

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

with open('cookies.json', 'r', encoding='utf-8') as f:
    cookies = json.load(f)

# ==========================================
# SISTEMA DE SALVAR CONFIG EM TEMPO REAL
# ==========================================

def save_config():
    """Salva as alterações no config.json em tempo real"""
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print("💾 Config atualizado e salvo no disco!")

# ==========================================
# CARREGAMENTO DE COMANDOS E EVENTOS
# ==========================================

def carregar_comandos():
    comandos = {}
    cmds_path = os.path.join(os.getcwd(), "scripts", "cmds")
    if os.path.exists(cmds_path):
        for filename in os.listdir(cmds_path):
            if filename.endswith(".py"):
                nome_modulo = filename[:-3]
                spec = importlib.util.spec_from_file_location(f"cmd_{nome_modulo}", os.path.join(cmds_path, filename))
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo)
                if hasattr(modulo, "cmd") and hasattr(modulo, "name"):
                    comandos[modulo.name] = modulo.cmd
                    print(f"✅ Comando carregado: {modulo.name}")
    return comandos

def carregar_eventos():
    eventos = []
    events_path = os.path.join(os.getcwd(), "scripts", "events")
    if os.path.exists(events_path):
        for filename in os.listdir(events_path):
            if filename.endswith(".py"):
                nome_modulo = filename[:-3]
                spec = importlib.util.spec_from_file_location(f"evt_{nome_modulo}", os.path.join(events_path, filename))
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.(modulo)
                if hasattr(modulo, "event"):
                    eventos.append(modulo.event)
                    print(f"✅ Evento carregado: {nome_modulo}")
    return eventos

comandos = carregar_comandos()
eventos = carregar_eventos()

# ==========================================
# FUNÇÕES AUXILIARES DE PERMISSÃO
# ==========================================

def is_owner(user_id):
    return str(user_id) in config["permissions"]["owner"]

def is_admin(user_id):
    return str(user_id) in config["permissions"]["admin"]

def is_whitelist(user_id):
    return str(user_id) in config["permissions"]["whitelist"]

def is_blacklisted(user_id, thread_id):
    return (str(user_id) in config["permissions"]["blacklist"]["users"] or 
            str(thread_id) in config["permissions"]["blacklist"]["threads"])

# ==========================================
# SISTEMA DE PUSH AUTOMÁTICO PARA O GITHUB
# ==========================================

last_push_time = 0
PUSH_INTERVAL = 300  # 5 minutos

def push_config_to_github():
    """Faz commit e push do config.json para o repositório"""
    global last_push_time
    
    current_time = time.time()
    
    if current_time - last_push_time < PUSH_INTERVAL:
        return
    
    try:
        subprocess.run(["git", "add", "config.json"], check=True)
        subprocess.run(["git", "commit", "-m", f"🤖 Config atualizado em {datetime.datetime.now()}"], check=True)
        subprocess.run(["git", "push"], check=True)
        
        last_push_time = current_time
        print("📤 Config enviado para o GitHub com sucesso!")
        
    except subprocess.CalledProcessError:
        pass
    except Exception as e:
        print(f"❌ Erro ao fazer push: {e}")
# ==========================================
# GESTÃO DE LISTAS VIA COMANDOS (REAL TIME)
# ==========================================

async def handle_admin_commands(cmd_name, args, author_id, thread_id, thread_type):
    if not is_owner(author_id):
        return

    if cmd_name == "addadmin":
        target_uid = args[0] if args else None
        if target_uid:
            if target_uid not in config["permissions"]["admin"]:
                config["permissions"]["admin"].append(target_uid)
                save_config()
                await client.sendMessage(f"✅ {target_uid} agora é admin.", thread_id, thread_type)

    elif cmd_name == "removeadmin":
        target_uid = args[0] if args else None
        if target_uid and target_uid in config["permissions"]["admin"]:
            config["permissions"]["admin"].remove(target_uid)
            save_config()
            await client.sendMessage(f"❌ {target_uid} não é mais admin.", thread_id, thread_type)

    elif cmd_name == "ban":
        target_uid = args[0] if args else None
        if target_uid:
            if target_uid not in config["permissions"]["blacklist"]["users"]:
                config["permissions"]["blacklist"]["users"].append(target_uid)
                save_config()
                await client.sendMessage(f"🚫 {target_uid} foi banido.", thread_id, thread_type)

    elif cmd_name == "unban":
        target_uid = args[0] if args else None
        if target_uid and target_uid in config["permissions"]["blacklist"]["users"]:
            config["permissions"]["blacklist"]["users"].remove(target_uid)
            save_config()
            await client.sendMessage(f"✅ {target_uid} foi desbanido.", thread_id, thread_type)

    elif cmd_name == "whitelist":
        target_uid = args[0] if args else None
        if target_uid:
            if target_uid not in config["permissions"]["whitelist"]:
                config["permissions"]["whitelist"].append(target_uid)
                save_config()
                await client.sendMessage(f"➕ {target_uid} adicionado à whitelist.", thread_id, thread_type)

    elif cmd_name == "unwhitelist":
        target_uid = args[0] if args else None
        if target_uid and target_uid in config["permissions"]["whitelist"]:
            config["permissions"]["whitelist"].remove(target_uid)
            save_config()
            await client.sendMessage(f"➖ {target_uid} removido da whitelist.", thread_id, thread_type)

# ==========================================
# HANDLER PRINCIPAL (CORPO DO BOT)
# ==========================================

async def handler(message_object, thread_id, thread_type, author_id):
    prefix = config["bot"]["prefix"]
    
    if is_blacklisted(author_id, thread_id):
        return
    
    if config["features"]["allow_events_without_prefix"]:
        for evento in eventos:
            try:
                await evento(message_object, thread_id, thread_type)
            except Exception as e:
                print(f"Erro no evento: {e}")
    
    if not message_object.text or not message_object.text.startswith(prefix):
        return

    parts = message_object.text.split(" ")
    cmd_name = parts[0][1:].lower()
    args = parts[1:]

    admin_commands = ["addadmin", "removeadmin", "ban", "unban", "whitelist", "unwhitelist"]
    if cmd_name in admin_commands:
        await handle_admin_commands(cmd_name, args, author_id, thread_id, thread_type)
        return

    if cmd_name in comandos and (is_owner(author_id) or is_admin(author_id) or is_whitelist(author_id)):
        delay_min = config["system"]["anti_ban"]["random_delay_min"]
        delay_max = config["system"]["anti_ban"]["random_delay_max"]
        await asyncio.sleep(random.uniform(delay_min, delay_max))

        try:
            await comandos[cmd_name](message_object, thread_id, thread_type, config)
        except Exception as e:
            print(f"Erro no comando {cmd_name}: {e}")
            await client.sendMessage("❌ Erro interno no comando.", thread_id, thread_type)

    elif cmd_name in comandos:
        await client.sendMessage("⛔ Você não tem permissão para usar esse comando.", thread_id, thread_type)

# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================

async def main():
    global client
    client = Client(cookies=cookies)
    print("🤖 Bot iniciado e raiz! Logado com sucesso.")
    
    @client.on("message")
    async def on_message(message_object):
        if not message_object.is_unsent:
            author_id = message_object.author.id
            thread_id = message_object.thread.id
            thread_type = message_object.thread.type
            await handler(message_object, thread_id, thread_type, author_id)
    
    while True:
        await asyncio.sleep(1)
        push_config_to_github()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot encerrado manualmente.")
        sys.exit(0)
