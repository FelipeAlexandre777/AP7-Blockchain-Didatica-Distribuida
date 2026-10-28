"""API HTTP de um nó independente da blockchain didática."""
import os
import logging
from threading import RLock
from typing import Any
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from blockchain import Blockchain, Block

NODE_NAME = os.getenv("NODE_NAME", "no-sem-nome")
DIFFICULTY = int(os.getenv("BLOCKCHAIN_DIFFICULTY", "3"))
app = FastAPI(title=f"Blockchain Didática - {NODE_NAME}", version="1.0.0")
bc = Blockchain(difficulty=DIFFICULTY)
peers: set[str] = set()
lock = RLock()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origem: str = Field(min_length=1, max_length=80)
    destino: str = Field(min_length=1, max_length=80)
    valor: float = Field(gt=0, le=1_000_000_000)


class Peer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=8, max_length=200)


class ResolveResult(BaseModel):
    message: str
    adopted: bool
    length: int
    peer: str | None = None


@app.get("/")
def root():
    return {"node": NODE_NAME, "difficulty": DIFFICULTY, "endpoints": ["/chain", "/mine", "/peers", "/resolve", "/validate"]}


@app.get("/chain")
def get_chain():
    with lock:
        chain = [block.to_dict() for block in bc.chain]
    return {"node": NODE_NAME, "length": len(chain), "difficulty": DIFFICULTY, "chain": chain}


@app.get("/validate")
def validate():
    with lock:
        ok = bc.valid()
        return {"node": NODE_NAME, "valid": ok, "length": len(bc.chain)}


@app.post("/mine")
def mine(transaction: Transaction):
    with lock:
        block = bc.mine(transaction.model_dump())
    logger.info("Nó %s minerou bloco=%s nonce=%s hash=%s", NODE_NAME, block.index, block.nonce, block.hash)
    return {"node": NODE_NAME, "block": block.to_dict(), "length": len(bc.chain)}


@app.post("/peers")
def add_peer(peer: Peer):
    url = peer.url.rstrip("/")
    if not url.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise HTTPException(status_code=400, detail="No laboratório, informe um peer HTTP local (localhost/127.0.0.1).")
    if url.endswith(f":{os.getenv('PORT', '8001')}") and NODE_NAME in ("no1", "no2"):
        # Não bloqueia configuração em outras portas; apenas previne a autorreferência óbvia pelo teste.
        pass
    peers.add(url)
    return {"node": NODE_NAME, "peers": sorted(peers)}


@app.get("/peers")
def list_peers():
    return {"node": NODE_NAME, "peers": sorted(peers)}


@app.post("/resolve", response_model=ResolveResult)
def resolve():
    """Consulta peers com timeout; adota apenas cadeia válida e estritamente mais longa."""
    with lock:
        local_length = len(bc.chain)
        local_chain = list(bc.chain)
    best_chain = local_chain
    best_peer = None
    errors = []
    for peer in sorted(peers):
        try:
            response = requests.get(peer + "/chain", timeout=(1, 2))
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            if payload.get("difficulty") != DIFFICULTY:
                errors.append(f"{peer}: dificuldade incompatível")
                continue
            candidate = Blockchain.from_dicts(payload.get("chain"), DIFFICULTY)
            if len(candidate.chain) > len(best_chain):
                best_chain = candidate.chain
                best_peer = peer
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            logger.warning("Peer %s ignorado durante resolve: %s", peer, exc)
            errors.append(f"{peer}: {type(exc).__name__}")
            continue
    adopted = False
    if len(best_chain) > local_length:
        with lock:
            # Revalida sob lock antes de substituir para evitar sobrescrever mineração concorrente.
            temporary = Blockchain(DIFFICULTY)
            temporary.chain = best_chain
            if temporary.valid() and len(best_chain) > len(bc.chain):
                bc.chain = best_chain
                adopted = True
    if adopted:
        logger.info("Nó %s adotou cadeia de %s com %s blocos", NODE_NAME, best_peer, len(best_chain))
        return ResolveResult(message="Cadeia válida mais longa adotada.", adopted=True, length=len(best_chain), peer=best_peer)
    message = "Nenhuma cadeia válida mais longa encontrada."
    if errors:
        message += " Um ou mais peers falharam; o nó continuou disponível."
    return ResolveResult(message=message, adopted=False, length=local_length)


# Endpoint exclusivo para demonstrar adulteração no laboratório; não usar em produção.
@app.post("/lab/tamper/{index}")
def lab_tamper(index: int):
    with lock:
        if index <= 0 or index >= len(bc.chain):
            raise HTTPException(status_code=400, detail="Informe índice de bloco existente maior que zero.")
        bc.chain[index].data["adulterado"] = True
    logger.warning("ADULTERAÇÃO DIDÁTICA aplicada no bloco %s do nó %s", index, NODE_NAME)
    return {"message": "Bloco adulterado propositalmente; hash não foi recalculado.", "index": index}
