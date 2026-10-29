import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Caixa", page_icon="📱", layout="centered")

def conectar_banco():
    conn = sqlite3.connect('caixa.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, custo REAL, venda REAL, estoque INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Vendas (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER, qtd INTEGER, pagamento TEXT, total REAL, data_hora TEXT)''')
    # Tabela nova para gerenciar os turnos!
    cursor.execute('''CREATE TABLE IF NOT EXISTS Fechamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT)''')
    conn.commit()
    return conn

conn = conectar_banco()

st.title("📱 Caixa Rápido")
aba_vender, aba_estoque, aba_resumo = st.tabs(["🛒 Vender", "📦 Estoque", "📊 Resumo"])

# --- 1. VENDER ---
with aba_vender:
    df_prod = pd.read_sql_query("SELECT * FROM Produtos", conn)
    if not df_prod.empty:
        opcoes = df_prod.apply(lambda r: f"{r['nome']} - R$ {r['venda']:.2f} (Restam: {r['estoque']})", axis=1).tolist()
        produto_sel = st.selectbox("O que está vendendo?", opcoes)
        
        idx = opcoes.index(produto_sel)
        id_prod = int(df_prod.iloc[idx]['id'])
        venda_un = float(df_prod.iloc[idx]['venda'])
        estoque_atual = int(df_prod.iloc[idx]['estoque'])
        
        qtd = st.number_input("Quantidade:", min_value=1, value=1)
        st.info(f"Total a cobrar: **R$ {qtd * venda_un:.2f}**")
        
        pagamento = st.radio("Como o cliente pagou?", ["Pix", "Dinheiro", "Cartão"], horizontal=True)
        
        if st.button("✅ FECHAR VENDA", use_container_width=True, type="primary"):
            if estoque_atual >= qtd:
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Vendas (produto_id, qtd, pagamento, total, data_hora) VALUES (?, ?, ?, ?, ?)", (id_prod, qtd, pagamento, qtd * venda_un, agora))
                cursor.execute("UPDATE Produtos SET estoque = estoque - ? WHERE id = ?", (qtd, id_prod))
                conn.commit()
                st.success("Venda registrada com sucesso!")
            else:
                st.error("Estoque insuficiente. Reponha na aba Estoque.")
    else:
        st.warning("Vá na aba 'Estoque' e cadastre os produtos primeiro.")

# --- 2. ESTOQUE ---
with aba_estoque:
    st.subheader("O que temos na loja:")
    df_est = pd.read_sql_query("SELECT nome as Produto, estoque as Quantidade, venda as Preço FROM Produtos", conn)
    if not df_est.empty:
        st.dataframe(df_est, hide_index=True, use_container_width=True)
    else:
        st.write("Nenhum produto cadastrado ainda.")
    
    with st.expander("📥 Repor um produto que chegou"):
        if not df_prod.empty:
            prod_rep = st.selectbox("Qual produto repor?", df_prod['nome'].tolist())
            qtd_rep = st.number_input("Quantas unidades chegaram?", min_value=1, value=12)
            if st.button("Atualizar Estoque"):
                id_rep = int(df_prod[df_prod['nome'] == prod_rep]['id'].values[0])
                cursor = conn.cursor()
                cursor.execute("UPDATE Produtos SET estoque = estoque + ? WHERE id = ?", (qtd_rep, id_rep))
                conn.commit()
                st.success("Estoque atualizado! Recarregue a página.")
                
    with st.expander("➕ Cadastrar Bebida Nova"):
        nome = st.text_input("Nome (ex: Coca 2L)")
        custo = st.number_input("Preço de Custo", format="%.2f")
        venda = st.number_input("Preço de Venda", format="%.2f")
        if st.button("Salvar Produto Novo"):
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Produtos (nome, custo, venda) VALUES (?, ?, ?)", (nome, custo, venda))
            conn.commit()
            st.success(f"Produto {nome} cadastrado! Recarregue a página.")

    with st.expander("🗑️ Apagar um Produto"):
        if not df_prod.empty:
            prod_apagar = st.selectbox("Qual produto deseja excluir?", df_prod['nome'].tolist())
            st.warning("Atenção: O produto será removido da lista definitivamente.")
            if st.button("🚨 Apagar Produto"):
                id_apagar = int(df_prod[df_prod['nome'] == prod_apagar]['id'].values[0])
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Produtos WHERE id = ?", (id_apagar,))
                conn.commit()
                st.success(f"[{prod_apagar}] excluído com sucesso! Recarregue a página.")

# --- 3. RESUMO ---
with aba_resumo:
    cursor = conn.cursor()
    
    # 1. Descobre a data do último fechamento de caixa
    cursor.execute("SELECT data_hora FROM Fechamentos ORDER BY id DESC LIMIT 1")
    ultimo_fechamento = cursor.fetchone()
    
    # 2. Puxa apenas as vendas feitas DEPOIS do último fechamento
    if ultimo_fechamento:
        data_corte = ultimo_fechamento[0]
        st.caption(f"Caixa aberto desde: {data_corte}")
        query_vendas = f"SELECT Vendas.id as ID, COALESCE(Produtos.nome, 'Produto Apagado') as Produto, Vendas.qtd as Qtd, Vendas.total as Valor, Vendas.pagamento as Pagamento FROM Vendas LEFT JOIN Produtos ON Vendas.produto_id = Produtos.id WHERE Vendas.data_hora > '{data_corte}'"
    else:
        st.caption("Primeiro turno de uso do sistema.")
        query_vendas = "SELECT Vendas.id as ID, COALESCE(Produtos.nome, 'Produto Apagado') as Produto, Vendas.qtd as Qtd, Vendas.total as Valor, Vendas.pagamento as Pagamento FROM Vendas LEFT JOIN Produtos ON Vendas.produto_id = Produtos.id"

    df_vendas_turno = pd.read_sql_query(query_vendas, conn)
    
    # 3. Mostra os números do turno atual
    if not df_vendas_turno.empty:
        total_turno = df_vendas_turno['Valor'].sum()
        st.metric("Caixa Atual (Neste turno)", f"R$ {total_turno:.2f}")
        
        st.write("Vendas deste turno:")
        st.dataframe(df_vendas_turno, hide_index=True, use_container_width=True)
        
        with st.expander("↩️ Cancelar uma Venda Deste Turno"):
            opcoes_venda = df_vendas_turno.apply(lambda r: f"ID: {r['ID']} | {r['Produto']} | R$ {r['Valor']:.2f}", axis=1).tolist()
            venda_cancelar = st.selectbox("Selecione a venda errada:", opcoes_venda)
            
            if st.button("🚨 Cancelar Venda e Devolver Estoque"):
                idx_v = opcoes_venda.index(venda_cancelar)
                id_venda_real = int(df_vendas_turno.iloc[idx_v]['ID'])
                
                cursor.execute("SELECT produto_id, qtd FROM Vendas WHERE id = ?", (id_venda_real,))
                dados_v = cursor.fetchone()
                if dados_v:
                    p_id, p_qtd = dados_v
                    if p_id:
                        cursor.execute("UPDATE Produtos SET estoque = estoque + ? WHERE id = ?", (p_qtd, p_id))
                    cursor.execute("DELETE FROM Vendas WHERE id = ?", (id_venda_real,))
                    conn.commit()
                    st.success("Venda cancelada! Caixa e estoque corrigidos. Recarregue a página.")
                    
        # Botão de Fechar o Dia
        st.divider()
        st.subheader("🔒 Encerrar Turno")
        st.write("Ao encerrar, o caixa zera para o próximo turno (ex: tarde ou amanhã). O valor total fica salvo no histórico.")
        if st.button("Encerrar o Caixa Agora", type="primary"):
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO Fechamentos (data_hora) VALUES (?)", (agora,))
            conn.commit()
            st.success("Caixa encerrado com sucesso! Recarregue a página para iniciar o novo turno zerado.")
    else:
        st.metric("Caixa Atual (Neste turno)", "R$ 0,00")
        st.info("Nenhuma venda registrada neste turno ainda.")

    # 4. A Gaveta de Histórico (Pra ela ver o que já foi fechado e não perder o controle)
    with st.expander("📚 Histórico Geral (Ver dias/turnos anteriores)"):
        df_todas = pd.read_sql_query("SELECT SUBSTR(Vendas.data_hora, 1, 16) as Data, COALESCE(Produtos.nome, 'Produto Apagado') as Produto, Vendas.qtd as Qtd, Vendas.total as Valor, Vendas.pagamento as Pagamento FROM Vendas LEFT JOIN Produtos ON Vendas.produto_id = Produtos.id ORDER BY Vendas.id DESC LIMIT 100", conn)
        if not df_todas.empty:
            st.dataframe(df_todas, hide_index=True, use_container_width=True)
        else:
            st.write("Histórico vazio.")
