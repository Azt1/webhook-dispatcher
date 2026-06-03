# Webhook Dispatcher

Uma fila local para enviar eventos JSON a webhooks. A ideia é guardar o evento antes de enviá-lo, para poder tentar novamente se o destino estiver indisponível.

O projeto usa Python e SQLite. Não precisa de serviço de filas nem de bibliotecas externas em tempo de execução.
