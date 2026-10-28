import unittest
from blockchain import Blockchain, Block


class BlockchainTests(unittest.TestCase):
    def setUp(self):
        self.bc = Blockchain(difficulty=2)

    def test_genesis_and_valid_chain(self):
        self.assertEqual(self.bc.chain[0].index, 0)
        self.assertTrue(self.bc.valid())
        self.bc.mine({"origem": "A", "destino": "B", "valor": 1})
        self.assertTrue(self.bc.valid())

    def test_detects_tampering(self):
        self.bc.mine({"origem": "A", "destino": "B", "valor": 1})
        self.bc.chain[1].data["valor"] = 99
        self.assertFalse(self.bc.valid())

    def test_detects_wrong_previous_hash(self):
        self.bc.mine({"origem": "A", "destino": "B", "valor": 1})
        self.bc.chain[1].previous_hash = "f" * 64
        self.assertFalse(self.bc.valid())

    def test_requires_proof_of_work(self):
        self.bc.mine({"origem": "A", "destino": "B", "valor": 1})
        self.bc.chain[1].nonce = 0
        self.bc.chain[1].hash = self.bc.chain[1].calculate_hash()
        self.assertFalse(self.bc.valid())

    def test_rejects_invalid_serialized_chain(self):
        payload = [block.to_dict() for block in self.bc.chain]
        payload[0]["data"] = {"msg": "changed"}
        with self.assertRaises(ValueError):
            Blockchain.from_dicts(payload, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
