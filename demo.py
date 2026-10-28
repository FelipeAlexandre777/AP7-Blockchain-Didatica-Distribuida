"""Demonstração reproduzível: PoW, adulteração, fork e reconciliação entre dois nós."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
processes = []
session = requests.Session()


def wait_ready(url, process, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        if process.poll() is not None:
            raise RuntimeError(f"Servidor encerrou inesperadamente. Consulte {LOGS}.")
        try:
            r = session.get(url + "/", timeout=0.5)
            if r.ok:
                return
        except requests.RequestException:
            time.sleep(0.25)
    raise TimeoutError(f"Nó não iniciou: {url}")


def post(url, path, payload=None):
    r = session.post(url + path, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def get(url, path):
    r = session.get(url + path, timeout=5)
    r.raise_for_status()
    return r.json()


def start_node(name, port):
    env = os.environ.copy()
    env["NODE_NAME"] = name
    env["BLOCKCHAIN_DIFFICULTY"] = "2"
    env["PORT"] = str(port)
    log_path = LOGS / f"{name}.log"
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "node:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env, stdout=log_file, stderr=subprocess.STDOUT
    )
    processes.append((proc, log_file, name))
    return f"http://127.0.0.1:{port}", proc


def main():
    a = b = None
    try:
        print("AP7 - Blockchain Didática Distribuída")
        a, pa = start_node("no1", 8001)
        b, pb = start_node("no2", 8002)
        wait_ready(a, pa)
        wait_ready(b, pb)
        print("[1/6] Dois nós independentes iniciados (portas 8001 e 8002).")

        # Ambos mineram um bloco próprio, gerando um fork com mesma altura.
        post(a, "/mine", {"origem": "Alice", "destino": "Bruno", "valor": 10.0})
        post(b, "/mine", {"origem": "Carla", "destino": "Daniel", "valor": 7.5})
        ca, cb = get(a, "/chain"), get(b, "/chain")
        assert ca["length"] == cb["length"] == 2
        assert ca["chain"][-1]["hash"] != cb["chain"][-1]["hash"]
        print("[2/6] Fork controlado: ambos têm 2 blocos, mas os hashes do bloco 1 divergem.")

        # Nó A avança mais um bloco. B registra A como peer e reconcilia.
        post(a, "/mine", {"origem": "Eva", "destino": "Fábio", "valor": 3.25})
        post(b, "/peers", {"url": a})
        before = get(b, "/chain")["length"]
        result = post(b, "/resolve")
        after = get(b, "/chain")["length"]
        assert result["adopted"] and after == 3 and after > before
        assert get(b, "/validate")["valid"]
        print(f"[3/6] Reconciliação: nó B adotou cadeia válida mais longa; tamanho {before} -> {after}.")

        # A adulteração de conteúdo sem recalcular o hash deve ser detectada.
        post(b, "/lab/tamper/1")
        validation = get(b, "/validate")
        assert validation["valid"] is False
        print("[4/6] Adulteração sem recálculo detectada: /validate retornou valid=false.")

        # Restaura B via reinício do processo para continuar demonstração limpa de peer indisponível.
        # O encerramento do processo é controlado e a API do outro nó continua respondendo.
        print("[5/6] Encerrando nó A para testar falha parcial.")
        for proc, log_file, name in processes:
            if name == "no1":
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        try:
            post(b, "/resolve")
            print("[6/6] Peer indisponível tratado: nó B continuou respondendo sem encerrar.")
        except requests.RequestException as exc:
            raise RuntimeError(f"Nó B deveria permanecer disponível: {exc}")

        evidence = {
            "fork": {"no1_initial_length": 2, "no2_initial_length": 2, "different_hashes": True},
            "reconciliation": {"adopted": result["adopted"], "length_after": after, "valid_after_adoption": True},
            "tampering": {"valid_after_tamper": validation["valid"]},
            "peer_unavailable": {"no2_available_after_no1_stopped": True},
        }
        (LOGS / "evidencias.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Evidências gravadas em: {LOGS / 'evidencias.json'}")
        print("Demonstração concluída.")
    finally:
        for proc, log_file, name in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
            log_file.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERRO NA DEMONSTRAÇÃO: {exc}")
        print("Consulte os arquivos da pasta logs/ e verifique se as portas 8001/8002 estão livres.")
        sys.exit(1)
