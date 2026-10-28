"""AuroraArm — pacote de design baseado em modelos da junta do cotovelo.

Módulos:
    parametros    -> leitura dos parâmetros físicos (parametros.json)
    planta        -> modelo em espaço de estados, discretização e simulação
    identificacao -> identificação por mínimos quadrados e validação
    controlador   -> PID discreto com saturação, limite de corrente e anti-windup
    supervisor    -> máquina de estados do supervisor de segurança (modelo formal)
    verificacao   -> model checker explícito (segurança com prazo e vivacidade)
    testes_modelo -> geração de testes por percurso do grafo do supervisor
    codegen       -> geração automática do código C a partir do modelo
"""
