import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Depósito RL", page_icon="🍻", layout="centered")

def conectar_banco():
    # Banco novo para a versão com Fardos
    conn = sqlite3.connect('caixa_v4.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, custo REAL, venda_un REAL, venda_fardo REAL, qtd_fardo INTEGER, estoque INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Vendas (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER, tipo_venda TEXT, qtd INTEGER, pagamento TEXT, total REAL, data_hora TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Fechamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT)''')
    conn.commit()
    return conn

conn = conectar_banco()

# Cabeçalho Personalizado do Depósito RL
st.markdown("<h1 style='text-align: center; color: #FFBF00;'>🍻 Depósito RL</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888;'>Sistema de Gestão Profissional</p>", unsafe_allow_html=True)
st.divider()

aba_vender, aba_estoque, aba_resumo = st.tabs(["🛒 Vender", "📦 Estoque", "📊 Caixa e Histórico"])

# --- 1. VENDER ---
with aba_vender:
    df_prod = pd.read_sql_query("SELECT * FROM Produtos", conn)
    if not df_prod.empty:
        # Função para mostrar o estoque de forma inteligente (Ex: 2 Fardos e 3 Unidades)
        def formata_estoque(est, qtd_f):
            if qtd_f > 1:
                fardos = est // qtd_f
                unidades = est % qtd_f
                return f"{fardos} Fardo(s) e {unidades} Unid."
            return f"{est} Unid."

        opcoes = df_prod.apply(lambda r: f"{r['nome']} | {formata_estoque(r['estoque'], r['qtd_fardo'])}", axis=1).tolist()
        produto_sel = st.selectbox("O que está vendendo?", opcoes)
        
        idx = opcoes.index(produto_sel)
        id_prod = int(df_prod.iloc[idx]['id'])
        venda_un = float(df_prod.iloc[idx]['venda_un'])
        venda_fardo = float(df_prod.iloc[idx]['venda_fardo'])
        qtd_fardo = int(df_prod.iloc[idx]['qtd_fardo'])
        estoque_atual = int(df_prod.iloc[idx]['estoque'])
        
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.radio("Venda por:", ["Unidade", "Fardo Fechado"])
        with col2:
            qtd = st.number_input(f"Quantos(as) {tipo.lower()}s?", min_value=1, value=1)
        
        # Lógica matemática de venda
        if tipo == "Fardo Fechado":
            total_cobrar = qtd * venda_fardo
            qtd_descontar_estoque = qtd * qtd_fardo
            detalhe = f"(Total: {qtd_descontar_estoque} unidades soltas)"
        else:
            total_cobrar = qtd * venda_un
            qtd_descontar_estoque = qtd
            detalhe = ""

        st.info(f"Total a cobrar: **R$ {total_cobrar:.2f}** {detalhe}")
        
        pagamento = st.radio("Forma de Pagamento:", ["Pix", "Dinheiro", "Cartão"], horizontal=True)
        
        if st.button("✅ FECHAR VENDA", use_container_width=True, type="primary"):
            if estoque_atual >= qtd_descontar_estoque:
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Vendas (produto_id, tipo_venda, qtd, pagamento, total, data_hora) VALUES (?, ?, ?, ?, ?, ?)", (id_prod, tipo, qtd, pagamento, total_cobrar, agora))
                cursor.execute("UPDATE Produtos SET estoque = estoque - ? WHERE id = ?", (qtd_descontar_estoque, id_prod))
                conn.commit()
                st.success("Venda registrada com sucesso!")
            else:
                st.error(f"Estoque insuficiente. Você só tem {estoque_atual} unidades no total.")
    else:
        st.warning("Vá na aba 'Estoque' e cadastre os produtos primeiro.")

# --- 2. ESTOQUE ---
with aba_estoque:
    st.subheader("Controle de Prateleira")
    df_est = pd.read_sql_query("SELECT id, nome, venda_un, venda_fardo, qtd_fardo, estoque FROM Produtos", conn)
    
    if not df_est.empty:
        # Cria uma visualização rica
        df_view = df_est.copy()
        df_view['Preço Un.'] = df_view['venda_un'].apply(lambda x: f"R$ {x:.2f}")
        df_view['Preço Fardo'] = df_view['venda_fardo'].apply(lambda x: f"R$ {x:.2f}")
        df_view['Fardos Completos'] = df_view['estoque'] // df_view['qtd_fardo']
        df_view['Unidades Soltas'] = df_view['estoque'] % df_view['qtd_fardo']
        
        st.dataframe(df_view[['nome', 'Preço Un.', 'Preço Fardo', 'Fardos Completos', 'Unidades Soltas']], hide_index=True, use_container_width=True)
    else:
        st.write("Nenhum produto cadastrado ainda.")
    
    with st.expander("📥 Repor Mercadoria"):
        if not df_prod.empty:
            prod_rep = st.selectbox("O que chegou do caminhão?", df_prod['nome'].tolist())
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                tipo_rep = st.radio("Chegou em:", ["Fardos", "Unidades soltas"])
            with col_r2:
                qtd_rep = st.number_input("Quantidade que chegou:", min_value=1, value=1)
            
            if st.button("Atualizar Estoque"):
                id_rep = int(df_prod[df_prod['nome'] == prod_rep]['id'].values[0])
                fator = int(df_prod[df_prod['nome'] == prod_rep]['qtd_fardo'].values[0]) if tipo_rep == "Fardos" else 1
                qtd_final = qtd_rep * fator
                
                cursor = conn.cursor()
                cursor.execute("UPDATE Produtos SET estoque = estoque + ? WHERE id = ?", (qtd_final, id_rep))
                conn.commit()
                st.success(f"Estoque abastecido com mais {qtd_final} unidades no total! Atualize a página.")
                
    with st.expander("➕ Cadastrar Novo Produto"):
        st.caption("Dica: Se a bebida não tem fardo (ex: destilado), coloque 1 na quantidade do fardo e repita o preço.")
        nome = st.text_input("Nome (ex: Skol Lata 350ml)")
        custo = st.number_input("Custo Total (R$)", format="%.2f")
        
        c1, c2, c3 = st.columns(3)
        venda_un = c1.number_input("Preço de Venda (Unidade)", format="%.2f")
        qtd_f = c2.number_input("Quantas Unid. vem no Fardo?", min_value=1, value=12)
        venda_fardo = c3.number_input("Preço de Venda (Fardo)", format="%.2f")
        
        if st.button("Salvar Produto no Sistema"):
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Produtos (nome, custo, venda_un, venda_fardo, qtd_fardo) VALUES (?, ?, ?, ?, ?)", (nome, custo, venda_un, venda_fardo, qtd_f))
            conn.commit()
            st.success(f"[{nome}] cadastrado com sucesso! Atualize a página.")

# --- 3. RESUMO ---
with aba_resumo:
    cursor = conn.cursor()
    cursor.execute("SELECT data_hora FROM Fechamentos ORDER BY id DESC LIMIT 1")
    ultimo_fechamento = cursor.fetchone()
    
    if ultimo_fechamento:
        data_corte = ultimo_fechamento[0]
        st.caption(f"🟢 Caixa Aberto (Início: {data_corte})")
        query_vendas = f"SELECT Vendas.id, COALESCE(Produtos.nome, 'Produto Apagado') as Produto, Vendas.tipo_venda as Tipo, Vendas.qtd as Qtd, Vendas.total as Valor, Vendas.pagamento as Pagamento FROM Vendas LEFT JOIN Produtos ON Vendas.produto_id = Produtos.id WHERE Vendas.data_hora > '{data_corte}'"
    else:
        st.caption("🟢 Primeiro turno de uso do sistema.")
        query_vendas = "SELECT Vendas.id, COALESCE(Produtos.nome, 'Produto Apagado') as Produto, Vendas.tipo_venda as Tipo, Vendas.qtd as Qtd, Vendas.total as Valor, Vendas.pagamento as Pagamento FROM Vendas LEFT JOIN Produtos ON Vendas.produto_id = Produtos.id"

    df_vendas_turno = pd.read_sql_query(query_vendas, conn)
    
    if not df_vendas_turno.empty:
        total_turno = df_vendas_turno['Valor'].sum()
        st.metric("💰 Faturamento do Turno Atual", f"R$ {total_turno:.2f}")
        
        st.write("Vendas deste turno:")
        st.dataframe(df_vendas_turno, hide_index=True, use_container_width=True)
        
        st.divider()
        st.subheader("🔒 Fechar o Caixa")
        st.write("Guarda o dinheiro no histórico e zera a tela para o próximo turno.")
        if st.button("Encerrar Turno Agora", type="primary"):
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO Fechamentos (data_hora) VALUES (?)", (agora,))
            conn.commit()
            st.success("Caixa encerrado! Recarregue a página.")
    else:
        st.metric("💰 Faturamento do Turno Atual", "R$ 0,00")
        st.info("Aguardando as vendas de hoje...")

    with st.expander("📚 Consultar Histórico Geral (Fechamentos Anteriores)"):
        df_todas = pd.read_sql_query("SELECT SUBSTR(Vendas.data_hora, 1, 16) as Data, COALESCE(Produtos.nome, 'Produto Apagado') as Produto, Vendas.tipo_venda as Tipo, Vendas.qtd as Qtd, Vendas.total as Valor, Vendas.pagamento as Pagamento FROM Vendas LEFT JOIN Produtos ON Vendas.produto_id = Produtos.id ORDER BY Vendas.id DESC LIMIT 100", conn)
        if not df_todas.empty:
            st.dataframe(df_todas, hide_index=True, use_container_width=True)
        else:
            st.write("Histórico vazio.")
