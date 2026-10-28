"""Implementação didática de blocos, SHA-256, Proof of Work e validação."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


@dataclass
class Block:
    index: int
    timestamp: str
    data: dict[str, Any]
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def calculate_hash(self) -> str:
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        raw = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "Block":
        required = {"index", "timestamp", "data", "previous_hash", "nonce", "hash"}
        if not isinstance(value, dict) or set(value) != required:
            raise ValueError("Formato de bloco inválido.")
        if not isinstance(value["index"], int) or value["index"] < 0:
            raise ValueError("Índice inválido.")
        if not isinstance(value["timestamp"], str):
            raise ValueError("Timestamp inválido.")
        if not isinstance(value["data"], dict):
            raise ValueError("Data deve ser um objeto JSON.")
        if not isinstance(value["previous_hash"], str) or len(value["previous_hash"]) != 64:
            raise ValueError("previous_hash inválido.")
        if not isinstance(value["nonce"], int) or value["nonce"] < 0:
            raise ValueError("Nonce inválido.")
        if not isinstance(value["hash"], str) or len(value["hash"]) != 64:
            raise ValueError("Hash inválido.")
        return cls(**value)


class Blockchain:
    def __init__(self, difficulty: int = 3):
        if not isinstance(difficulty, int) or not 1 <= difficulty <= 5:
            raise ValueError("A dificuldade deve estar entre 1 e 5.")
        self.difficulty = difficulty
        self.chain: list[Block] = [self._genesis()]

    def _genesis(self) -> Block:
        block = Block(0, "GENESIS", {"msg": "genesis"}, "0" * 64)
        block.hash = block.calculate_hash()
        return block

    def mine(self, data: dict) -> Block:
        if not isinstance(data, dict):
            raise ValueError("Os dados do bloco devem ser um objeto.")
        block = Block(
            index=len(self.chain),
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
            previous_hash=self.chain[-1].hash,
        )
        target = "0" * self.difficulty
        while True:
            block.hash = block.calculate_hash()
            if block.hash.startswith(target):
                break
            block.nonce += 1
        self.chain.append(block)
        return block

    def valid(self) -> bool:
        if not self.chain:
            return False
        target = "0" * self.difficulty
        for i, block in enumerate(self.chain):
            if block.hash != block.calculate_hash():
                return False
            if i == 0:
                if (block.index != 0 or block.timestamp != "GENESIS"
                        or block.previous_hash != "0" * 64
                        or block.data != {"msg": "genesis"}):
                    return False
            else:
                previous = self.chain[i - 1]
                if block.index != i:
                    return False
                if block.previous_hash != previous.hash:
                    return False
                if not block.hash.startswith(target):
                    return False
        return True

    def replace_chain(self, candidate: list[Block]) -> None:
        """Substitui somente por uma cadeia válida e estritamente mais longa."""
        if len(candidate) <= len(self.chain):
            raise ValueError("A cadeia candidata não é mais longa.")
        temporary = Blockchain(self.difficulty)
        temporary.chain = candidate
        if not temporary.valid():
            raise ValueError("A cadeia candidata é inválida.")
        self.chain = candidate

    @classmethod
    def from_dicts(cls, values: list[dict], difficulty: int) -> "Blockchain":
        if not isinstance(values, list) or not values:
            raise ValueError("A cadeia recebida deve ser uma lista não vazia.")
        instance = cls(difficulty)
        instance.chain = [Block.from_dict(item) for item in values]
        if not instance.valid():
            raise ValueError("A cadeia recebida falhou na validação.")
        return instance
