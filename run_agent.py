"""
Script para executar o agente de atendimento localmente.
Permite testar o workflow do LangGraph via linha de comando.
"""
from agent import app
from langchain_core.messages import HumanMessage


def run_conversation():
    """Executa uma conversa interativa com o agente."""
    print("=" * 60)
    print("🤖 Sistema de Atendimento Inteligente - LangGraph")
    print("=" * 60)
    print("\nDigite 'sair' para encerrar a conversa.\n")
    
    while True:
        # Recebe input do usuário
        user_input = input("Você: ").strip()
        
        if user_input.lower() in ['sair', 'exit', 'quit']:
            print("\n👋 Até logo! Obrigado por usar nosso sistema.")
            break
        
        if not user_input:
            continue
        
        # Cria a mensagem do usuário
        initial_state = {
            "messages": [HumanMessage(content=user_input)]
        }
        
        # Executa o workflow
        try:
            result = app.invoke(initial_state)
            
            # Extrai a resposta do assistente
            if result and "messages" in result:
                last_message = result["messages"][-1]
                print(f"\n🤖 Assistente: {last_message.content}\n")
            else:
                print("\n⚠️ Nenhuma resposta foi gerada.\n")
                
        except Exception as e:
            print(f"\n❌ Erro ao processar mensagem: {e}\n")


def run_single_query(query: str):
    """Executa uma única consulta e retorna o resultado."""
    print(f"\n📨 Consulta: {query}")
    print("-" * 60)
    
    initial_state = {
        "messages": [HumanMessage(content=query)]
    }
    
    try:
        result = app.invoke(initial_state)
        
        if result and "messages" in result:
            last_message = result["messages"][-1]
            print(f"\n🤖 Resposta: {last_message.content}\n")
            
            # Mostra informações de debug
            if "message_type" in result:
                print(f"📊 Tipo de Mensagem: {result['message_type']}")
            if "next_node" in result:
                print(f"🔀 Próximo Node: {result['next_node']}")
        else:
            print("\n⚠️ Nenhuma resposta foi gerada.\n")
            
    except Exception as e:
        print(f"\n❌ Erro: {e}\n")


def main():
    """Função principal."""
    import sys
    
    # Se houver argumentos, executa uma única consulta
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_single_query(query)
    else:
        # Caso contrário, inicia modo interativo
        run_conversation()


if __name__ == "__main__":
    main()
