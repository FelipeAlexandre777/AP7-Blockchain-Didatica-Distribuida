# AP7 — Blockchain Didática Distribuída

**Disciplina:** Sistemas Distribuídos — OBBGSIN.037  
**Atividade:** AP7 — Construindo uma Blockchain Didática Distribuída  
**Tecnologias:** Python, FastAPI, Uvicorn, Requests e SHA-256

## 1. Objetivo

Implementar uma blockchain didática própria, sem biblioteca pronta de blockchain, para estudar blocos, encadeamento por hash, Proof of Work (PoW), validação, divergência entre nós e reconciliação via HTTP.

O projeto segue os requisitos descritos nas páginas 42–45 da apostila: classe `Block`, bloco gênese, hash anterior e atual, validação completa, adulteração detectada, dois nós independentes, fork controlado, reconciliação e análise de limitações.

## 2. Requisitos

- Windows 10/11
- Python 3.10 ou superior (recomendado Python 3.12/3.13)
- VS Code
- Extensão Python da Microsoft no VS Code

## 3. Preparar o ambiente no Windows

Abra a pasta do projeto no VS Code. No terminal PowerShell, execute:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação do ambiente, use apenas para a sessão atual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Alternativa sem ativar o ambiente: execute `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` e use `.\.venv\Scripts\python.exe` nos comandos seguintes.

## 4. Executar os testes unitários

```powershell
python -m unittest -v
```

Os testes verificam bloco gênese, mineração, detecção de adulteração, hash anterior, Proof of Work e rejeição de cadeia serializada inválida.

## 5. Demonstração automatizada (recomendado)

Com as dependências instaladas, execute:

```powershell
python demo.py
```

O script inicia dois processos Uvicorn independentes, nas portas 8001 e 8002, com dificuldade 2 para a demonstração terminar rapidamente. Ele demonstra:

1. Dois nós independentes.
2. Fork: cada nó minera um bloco diferente e suas cadeias divergem.
3. Nó A minera outro bloco, ficando com uma cadeia válida mais longa.
4. Nó B consulta o peer e adota a cadeia somente após reconstrução e validação.
5. Adulteração proposital de um bloco sem recalcular o hash, detectada por `/validate`.
6. Indisponibilidade do peer: o nó B continua respondendo.
7. Evidências em `logs/evidencias.json` e logs dos servidores em `logs/no1.log` e `logs/no2.log`.

O script encerra os processos ao terminar. Se as portas 8001 ou 8002 já estiverem ocupadas, feche os programas que as usam e tente novamente.

## 6. Executar manualmente os dois nós

Abra **dois terminais** no VS Code, ambos na pasta do projeto e com o ambiente virtual ativo.

Terminal 1:

```powershell
$env:NODE_NAME="no1"
$env:BLOCKCHAIN_DIFFICULTY="2"
python -m uvicorn node:app --host 127.0.0.1 --port 8001
```

Terminal 2:

```powershell
$env:NODE_NAME="no2"
$env:BLOCKCHAIN_DIFFICULTY="2"
python -m uvicorn node:app --host 127.0.0.1 --port 8002
```

Acesse a documentação interativa:
- http://127.0.0.1:8001/docs
- http://127.0.0.1:8002/docs

Cada processo tem seu próprio estado em memória. Encerrar e iniciar novamente um nó reinicia sua cadeia.

## 7. Teste manual do fork e da reconciliação

No Swagger (`/docs`) do nó 8001, execute `POST /mine` com:

```json
{"origem":"Alice","destino":"Bruno","valor":10.0}
```

No nó 8002, execute `POST /mine` com:

```json
{"origem":"Carla","destino":"Daniel","valor":7.5}
```

Consulte `GET /chain` nos dois nós. Ambos terão altura 2, mas o bloco 1 terá hashes diferentes: isso é o fork controlado.

Depois, no nó 8001, mine outro bloco:

```json
{"origem":"Eva","destino":"Fabio","valor":3.25}
```

No nó 8002, registre o peer usando `POST /peers`:

```json
{"url":"http://127.0.0.1:8001"}
```

Por fim, execute `POST /resolve` no nó 8002 e consulte `GET /chain` e `GET /validate`. O nó 2 deve adotar a cadeia válida mais longa.

Para testar a adulteração, no nó 8002 execute `POST /lab/tamper/1` e depois `GET /validate`. O resultado esperado é `valid: false`. O endpoint de adulteração existe exclusivamente para o laboratório.

## 8. Endpoints

| Método | Endpoint | Finalidade |
|---|---|---|
| GET | `/` | Informações do nó |
| GET | `/chain` | Retorna a cadeia e a dificuldade |
| GET | `/validate` | Valida a cadeia local |
| POST | `/mine` | Valida os dados e minera um bloco |
| GET | `/peers` | Lista peers conhecidos |
| POST | `/peers` | Registra um peer HTTP local |
| POST | `/resolve` | Adota uma cadeia válida estritamente mais longa |
| POST | `/lab/tamper/{index}` | Adulteração proposital para teste |

## 9. Decisão de reconciliação

A regra adotada é **cadeia válida estritamente mais longa**. O nó consulta os peers com timeout, verifica se a dificuldade coincide, reconstrói cada bloco, confere tipos e campos, e valida hash, encadeamento, índices e Proof of Work antes de substituir a cadeia local. Se um peer estiver indisponível ou enviar dados inválidos, ele é ignorado e o processo continua.

A regra é propositalmente didática: não resolve todos os problemas de consenso. Em caso de cadeias válidas de mesmo tamanho, o nó não troca de cadeia. A implementação também não agrega trabalho acumulado por cadeia; usa comprimento como critério simples, conforme a atividade.

## 10. Questões para análise

### 1. Que propriedade o Proof of Work acrescentou ao simples encadeamento?

Além de calcular um hash coerente, o bloco precisa encontrar um `nonce` cujo hash comece com uma quantidade definida de zeros. Isso exige tentativas computacionais. Alterar dados muda o hash e invalida a prova, exigindo nova mineração dos blocos afetados. Não torna a adulteração impossível, apenas mais custosa.

### 2. A regra de reconciliação pode perder transações?

Sim. Se uma cadeia local contém transações que não aparecem na cadeia válida mais longa adotada, elas deixam de constar no ledger ativo. O protótipo não tem mempool para guardar e reapresentar transações órfãs, nem garantias de finalização.

### 3. Como um nó malicioso poderia explorar a implementação?

Pode enviar cadeias grandes para consumir recursos, dados falsos, transações sem validade de negócio, ou tentar explorar a regra da cadeia mais longa. Timeouts e validação reduzem alguns riscos, mas não substituem limites de tamanho, autenticação, autorização, rate limiting, validação de transações, proteção contra Sybil e um protocolo de consenso resistente a adversários.

### 4. O que seria necessário para autenticar autoria de transações?

Cada participante teria um par de chaves criptográficas. A transação seria assinada com a chave privada e validada pelos nós com a chave pública associada a uma identidade confiável. Também seriam necessárias regras de gestão/revogação de chaves e proteção contra replay. Esta versão não implementa assinaturas.

### 5. Quais condições de rede podem manter forks temporários?

Particionamento de rede, latência, perda de pacotes, atrasos de propagação, nós desconectados e mineração simultânea podem fazer nós receberem blocos em ordens diferentes. Quando a comunicação volta, a regra de reconciliação pode convergir para uma cadeia, desde que as condições da regra sejam satisfeitas.

## 11. Limitações: protótipo versus blockchain de produção

| Aspecto | Este protótipo | Blockchain de produção |
|---|---|---|
| Descoberta de nós | Cadastro manual de peers | Descoberta e gestão de pares conforme protocolo |
| Autoria | Sem assinatura digital | Assinaturas e regras de identidade/chaves |
| Consenso | Cadeia válida mais longa | Protocolo específico, com análise de segurança |
| Resistência a ataques | Validação básica | Proteções contra Sybil, spam e adversários |
| Propagação | Consulta HTTP manual | Propagação P2P otimizada |
| Persistência | Estado em memória | Persistência e recuperação definidas |
| Transações | Estrutura simples de origem/destino/valor | Regras de validade e execução mais completas |
| Incentivos | Não existem | Podem existir conforme o protocolo |
| Dificuldade | Fixa e configurável | Pode haver ajuste conforme protocolo |
| Finalidade | Educacional | Garantias definidas pelo desenho e operação |

## 12. Estrutura do projeto

```text
AP7-Blockchain-Didatica-Distribuida/
├── blockchain.py
├── node.py
├── demo.py
├── test_blockchain.py
├── requirements.txt
├── README.md
├── .gitignore
└── logs/
    └── (gerado durante a demonstração)
```

## 13. O que entregar

- Pasta do projeto com o código-fonte.
- `README.md` com comandos e justificativas.
- `logs/evidencias.json` e logs gerados pela demonstração.
- Capturas de tela próprias mostrando os testes, os dois nós, o fork e a reconciliação.
- ZIP do projeto para envio no ambiente indicado pelo professor.

**Importante:** rode `python demo.py` no seu computador antes de entregar. As evidências geradas devem corresponder à execução real no seu Windows; não apresente logs ou capturas não executados como se fossem resultados reais.

## 14. Roteiro de apresentação (3–5 minutos)

1. Mostrar os dois nós e seus endpoints `/docs`.
2. Explicar `Block`, SHA-256, `previous_hash`, `nonce` e dificuldade PoW.
3. Mostrar o fork: duas cadeias com mesmo tamanho e hashes diferentes.
4. Mostrar `/resolve` adotando a cadeia válida mais longa.
5. Mostrar `/lab/tamper/1` e `/validate` retornando `false`.
6. Encerrar explicando que comprimento não equivale a consenso seguro e citar as limitações da tabela.
