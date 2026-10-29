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
                st.success("Estoque atualizado!")
                
    with st.expander("➕ Cadastrar Bebida Nova"):
        nome = st.text_input("Nome (ex: Coca 2L)")
        custo = st.number_input("Preço de Custo", format="%.2f")
        venda = st.number_input("Preço de Venda", format="%.2f")
        if st.button("Salvar Produto Novo"):
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Produtos (nome, custo, venda) VALUES (?, ?, ?)", (nome, custo, venda))
            conn.commit()
            st.success(f"Produto {nome} cadastrado!")

# --- 3. RESUMO ---
with aba_resumo:
    hoje = datetime.now().strftime("%Y-%m-%d")
    df_vendas = pd.read_sql_query("SELECT * FROM Vendas", conn)
    
    if not df_vendas.empty:
        df_vendas['data_hora'] = pd.to_datetime(df_vendas['data_hora'])
        vendas_hoje = df_vendas[df_vendas['data_hora'].dt.date == datetime.now().date()]
        
        st.metric("Entrou no Caixa Hoje", f"R$ {vendas_hoje['total'].sum():.2f}")
        
        st.write("Vendas Feitas Hoje:")
        df_display = pd.read_sql_query(f"SELECT Produtos.nome as Produto, Vendas.qtd as Qtd, Vendas.total as Valor, Vendas.pagamento FROM Vendas JOIN Produtos ON Vendas.produto_id = Produtos.id WHERE Vendas.data_hora LIKE '{hoje}%'", conn)
        st.dataframe(df_display, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada ainda.")
