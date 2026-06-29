# Webhook Dispatcher

Uma fila local para enviar eventos JSON a webhooks. A ideia é guardar o evento antes de enviá-lo, para poder tentar novamente se o destino estiver indisponível.

O projeto usa Python e SQLite. Não precisa de serviço de filas nem de bibliotecas externas em tempo de execução.

## Como funciona

Você adiciona um arquivo JSON à fila e executa o processamento. Cada evento recebe um identificador e fica salvo no banco, com o número de tentativas e a resposta HTTP.

- Uma resposta HTTP 2xx marca o evento como entregue.
- Falhas de conexão, HTTP 408, 429 e 5xx permitem nova tentativa.
- Outros erros encerram o envio daquele evento.
- Por padrão, são até três tentativas, com esperas de 30 e 60 segundos entre elas.

O comando `run` processa até 100 eventos disponíveis e encerra. Para processar os reenvios, execute novamente após o intervalo. Para uso contínuo, ele pode ser chamado pelo Agendador de Tarefas do Windows ou pelo cron.

## Testar no computador

Use Python 3.11 ou mais recente. No PowerShell, dentro da pasta do projeto:

```powershell
$env:PYTHONPATH = "src"
python examples/receiver.py
```

Deixe esse terminal aberto. Em outro terminal, na mesma pasta:

```powershell
$env:PYTHONPATH = "src"
python -m webhook_dispatcher enqueue http://127.0.0.1:9000/events examples/order.json
python -m webhook_dispatcher run
python -m webhook_dispatcher list
```

O primeiro terminal mostra o pedido recebido. Na consulta da fila, o evento deve aparecer com status `delivered` e código HTTP `204`. Use Ctrl+C para encerrar o receptor.

O banco fica em `data/events.db`, fora do Git. Para usar outro arquivo, passe `--db` antes do comando:

```powershell
python -m webhook_dispatcher --db data/teste.db list
```

Você também pode instalar o pacote com `python -m pip install -e .` e usar o comando `webhook-dispatcher`.

## Testes

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Os testes usam bancos temporários e um receptor HTTP local. Eles verificam a persistência, os erros de entrada, as respostas HTTP e os reenvios.

## Limitações

Esta versão foi feita para um único processo de envio por banco. Não execute dois comandos `run` ao mesmo tempo no mesmo arquivo SQLite.

O identificador do evento segue no cabeçalho `Idempotency-Key`. O destino precisa usar essa chave para impedir duplicações: uma falha depois de o servidor receber o evento pode resultar em outro envio.

A fila guarda o JSON e o endereço de destino em texto no banco local. Use dados de exemplo na demonstração e HTTPS para destinos externos. O receptor de exemplo escuta apenas no computador local.

Ainda não há autenticação por destino, assinatura de webhooks, interface web ou suporte ao cabeçalho `Retry-After`.
