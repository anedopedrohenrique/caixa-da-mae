import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Depósito RL", page_icon="🍻", layout="centered")

def conectar_banco():
    conn = sqlite3.connect('caixa_v5.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, custo_fardo REAL, venda_un REAL, venda_fardo REAL, qtd_fardo INTEGER, estoque INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Vendas (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER, tipo_venda TEXT, qtd INTEGER, pagamento TEXT, total_venda REAL, custo_venda REAL, lucro REAL, data_hora TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Fechamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT)''')
    conn.commit()
    return conn

conn = conectar_banco()

# --- LOGO E CABEÇALHO OFICIAL DO DEPÓSITO RL ---
col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
with col_l2:
    st.image("https://raw.githubusercontent.com/anedopedrohenrique/caixa-da-mae/main/logo.png.jpeg", use_container_width=True)

st.markdown("<h1 style='text-align: center; color: #FFBF00;'>Depósito RL</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888888;'>Sistema de Gestão Profissional</p>", unsafe_allow_html=True)
st.divider()

aba_vender, aba_estoque, aba_resumo = st.tabs(["🛒 Vender", "📦 Estoque", "📊 Caixa e Lucro"])

# --- 1. VENDER ---
with aba_vender:
    df_prod = pd.read_sql_query("SELECT * FROM Produtos", conn)
    if not df_prod.empty:
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
        custo_fardo = float(df_prod.iloc[idx]['custo_fardo'])
        venda_un = float(df_prod.iloc[idx]['venda_un'])
        venda_fardo = float(df_prod.iloc[idx]['venda_fardo'])
        qtd_fardo = int(df_prod.iloc[idx]['qtd_fardo'])
        estoque_atual = int(df_prod.iloc[idx]['estoque'])
        
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.radio("Venda por:", ["Unidade", "Fardo Fechado"])
        with col2:
            qtd = st.number_input(f"Quantos(as) {tipo.lower()}s?", min_value=1, value=1)
        
        if tipo == "Fardo Fechado":
            total_cobrar = qtd * venda_fardo
            custo_da_venda = qtd * custo_fardo
            qtd_descontar_estoque = qtd * qtd_fardo
            detalhe = f"(Descontando {qtd_descontar_estoque} unidades do estoque)"
        else:
            total_cobrar = qtd * venda_un
            custo_da_venda = qtd * (custo_fardo / qtd_fardo)
            qtd_descontar_estoque = qtd
            detalhe = ""

        lucro_da_venda = total_cobrar - custo_da_venda

        st.info(f"Total a cobrar: **R$ {total_cobrar:.2f}** {detalhe}")
        pagamento = st.radio("Forma de Pagamento:", ["Pix", "Dinheiro", "Cartão"], horizontal=True)
        
        if st.button("✅ FECHAR VENDA", use_container_width=True, type="primary"):
            if estoque_atual >= qtd_descontar_estoque:
                agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Vendas (produto_id, tipo_venda, qtd, pagamento, total_venda, custo_venda, lucro, data_hora) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                               (id_prod, tipo, qtd, pagamento, total_cobrar, custo_da_venda, lucro_da_venda, agora))
                
                if tipo == "Fardo Fechado":
                    qtd_baixa = qtd * qtd_fardo
                else:
                    qtd_baixa = qtd
                    
                cursor.execute("UPDATE Produtos SET estoque = estoque - ? WHERE id = ?", (qtd_baixa, id_prod))
                conn.commit()
                st.success("Venda registrada! Dinheiro no caixa.")
            else:
                st.error(f"Estoque insuficiente. Você só tem {estoque_atual} unidades soltas.")
    else:
        st.warning("Vá na aba 'Estoque' e cadastre os produtos primeiro.")

# --- 2. ESTOQUE ---
with aba_estoque:
    st.subheader("Controle de Prateleira")
    df_est = pd.read_sql_query("SELECT id, nome, venda_un, venda_fardo, qtd_fardo, estoque FROM Produtos", conn)
    
    if not df_est.empty:
        df_view = df_est.copy()
        df_view['Preço Un.'] = df_view['venda_un'].apply(lambda x: f"R$ {x:.2f}")
        df_view['Preço Fardo'] = df_view['venda_fardo'].apply(lambda x: f"R$ {x:.2f}")
        df_view['Fardos'] = df_view['estoque'] // df_view['qtd_fardo']
        df_view['Unid. Soltas'] = df_view['estoque'] % df_view['qtd_fardo']
        st.dataframe(df_view[['nome', 'Preço Un.', 'Preço Fardo', 'Fardos', 'Unid. Soltas']], hide_index=True, use_container_width=True)
        
        with st.expander("📲 Gerar Cardápio para o WhatsApp (Clique aqui)"):
            st.write("Copie o texto abaixo e cole no seu Status ou mande para os clientes!")
            menu_texto = "🍻 *CARDÁPIO DEPÓSITO RL* 🍻\n\n"
            for _, row in df_est.iterrows():
                menu_texto += f"🍺 *{row['nome']}*\n"
                menu_texto += f"  🔹 Unidade: R$ {row['venda_un']:.2f}\n"
                if row['qtd_fardo'] > 1:
                    menu_texto += f"  📦 Fardo ({row['qtd_fardo']} un): R$ {row['venda_fardo']:.2f}\n"
                menu_texto += "\n"
            menu_texto += "📍 Entregas rápidas e bebida gelada!"
            st.text_area("Texto pronto para copiar:", menu_texto, height=200)
    else:
        st.write("Nenhum produto cadastrado ainda.")
    
    with st.expander("➕ Cadastrar Manualmente (1 por 1)"):
        st.caption("Dica: Se a bebida não tem fardo, coloque 1 na quantidade e repita o preço.")
        nome = st.text_input("Nome (ex: Skol Lata 350ml)")
        custo = st.number_input("Custo de 1 Fardo Fechado (R$)", format="%.2f")
        c1, c2, c3 = st.columns(3)
        venda_un = c1.number_input("Preço de Venda (Unidade)", format="%.2f")
        qtd_f = c2.number_input("Quantas Unid. vem no Fardo?", min_value=1, value=12)
        venda_fardo = c3.number_input("Preço de Venda (Fardo)", format="%.2f")
        
        if st.button("Salvar Produto no Sistema"):
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Produtos (nome, custo_fardo, venda_un, venda_fardo, qtd_fardo) VALUES (?, ?, ?, ?, ?)", (nome, custo, venda_un, venda_fardo, qtd_f))
            conn.commit()
            st.success(f"[{nome}] cadastrado com sucesso! Atualize a página.")

    with st.expander("📥 Repor Mercadoria Existente"):
        df_prod_rep = pd.read_sql_query("SELECT * FROM Produtos", conn)
        if not df_prod_rep.empty:
            prod_rep = st.selectbox("O que chegou do caminhão?", df_prod_rep['nome'].tolist())
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                tipo_rep = st.radio("Chegou em:", ["Fardos", "Unidades soltas"])
            with col_r2:
                qtd_rep = st.number_input("Quantidade que chegou:", min_value=1, value=1)
            
            if st.button("Atualizar Estoque"):
                id_rep = int(df_prod_rep[df_prod_rep['nome'] == prod_rep]['id'].values[0])
                fator = int(df_prod_rep[df_prod_rep['nome'] == prod_rep]['qtd_fardo'].values[0]) if tipo_rep == "Fardos" else 1
                qtd_final = qtd_rep * fator
                cursor = conn.cursor()
                cursor.execute("UPDATE Produtos SET estoque = estoque + ? WHERE id = ?", (qtd_final, id_rep))
                conn.commit()
                st.success("Estoque abastecido com sucesso! Atualize a página.")
        else:
            st.write("Cadastre um produto primeiro para poder repor.")

    # --- O BOTÃO DE EXCLUIR PRODUTO GARANTIDO AQUI ---
    with st.expander("🗑️ Apagar um Produto"):
        df_prod_del = pd.read_sql_query("SELECT * FROM Produtos", conn)
        if not df_prod_del.empty:
            prod_apagar = st.selectbox("Qual produto deseja excluir do sistema?", df_prod_del['nome'].tolist())
            st.warning("Atenção: O produto será removido da prateleira definitivamente.")
            if st.button("🚨 Apagar Produto Definitivamente"):
                id_apagar = int(df_prod_del[df_prod_del['nome'] == prod_apagar]['id'].values[0])
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Produtos WHERE id = ?", (id_apagar,))
                conn.commit()
                st.success(f"[{prod_apagar}] excluído com sucesso! Atualize a página.")
        else:
            st.write("Nenhum produto para apagar.")

# --- 3. RESUMO E LUCRO ---
with aba_resumo:
    cursor = conn.cursor()
    cursor.execute("SELECT data_hora FROM Fechamentos ORDER BY id DESC LIMIT 1")
    ultimo_fechamento = cursor.fetchone()
    
    if ultimo_fechamento:
        data_corte = ultimo_fechamento[0]
        st.caption(f"🟢 Caixa Aberto (Início: {data_corte})")
        query_vendas = f"SELECT Vendas.id, COALESCE(Produtos.nome, 'Produto Apagado') as Produto, Vendas.tipo_venda as Tipo, Vendas.qtd as Qtd, Vendas.total_venda as Valor, Vendas.lucro as Lucro, Vendas.pagamento as Pagamento FROM Vendas LEFT JOIN Produtos ON Vendas.produto_id = Produtos.id WHERE Vendas.data_hora > '{data_corte}'"
    else:
        st.caption("🟢 Primeiro turno de uso do sistema.")
        query_vendas = "SELECT Vendas.id, COALESCE(Produtos.nome, 'Produto Apagado') as Produto, Vendas.tipo_venda as Tipo, Vendas.qtd as Qtd, Vendas.total_venda as Valor, Vendas.lucro as Lucro, Vendas.pagamento as Pagamento FROM Vendas LEFT JOIN Produtos ON Vendas.produto_id = Produtos.id"

    df_vendas_turno = pd.read_sql_query(query_vendas, conn)
    
    if not df_vendas_turno.empty:
        total_bruto = df_vendas_turno['Valor'].sum()
        total_lucro = df_vendas_turno['Lucro'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("💰 Faturamento Bruto (Entrou)", f"R$ {total_bruto:.2f}")
        c2.metric("📈 Lucro Líquido Real (Sobrou)", f"R$ {total_lucro:.2f}")
        
        st.write("Vendas deste turno:")
        st.dataframe(df_vendas_turno[['id', 'Produto', 'Tipo', 'Qtd', 'Valor', 'Lucro', 'Pagamento']], hide_index=True, use_container_width=True)
        
        with st.expander("↩️ Cancelar uma Venda Deste Turno"):
            opcoes_venda = df_vendas_turno.apply(lambda r: f"ID: {r['id']} | {r['Produto']} ({r['Tipo']}) | R$ {r['Valor']:.2f}", axis=1).tolist()
            venda_cancelar = st.selectbox("Selecione a venda registrada errada:", opcoes_venda)
            
            if st.button("🚨 Cancelar Venda e Devolver ao Estoque"):
                idx_v = opcoes_venda.index(venda_cancelar)
                id_venda_real = int(df_vendas_turno.iloc[idx_v]['id'])
                
                cursor.execute("SELECT produto_id, tipo_venda, qtd FROM Vendas WHERE id = ?", (id_venda_real,))
                dados_v = cursor.fetchone()
                
                if dados_v:
                    p_id, p_tipo, p_qtd = dados_v
                    if p_id:
                        cursor.execute("SELECT qtd_fardo FROM Produtos WHERE id = ?", (p_id,))
                        res_f = cursor.fetchone()
                        fator_fardo = res_f[0] if res_f else 1
                        
                        qtd_devolver = (p_qtd * fator_fardo) if p_tipo == "Fardo Fechado" else p_qtd
                        cursor.execute("UPDATE Produtos SET estoque = estoque + ? WHERE id = ?", (qtd_devolver, p_id))
                    
                    cursor.execute("DELETE FROM Vendas WHERE id = ?", (id_venda_real,))
                    conn.commit()
                    st.success("Venda cancelada! Caixa e estoque corrigidos. Recarregue a página.")

        st.divider()
        st.subheader("🔒 Fechar o Caixa")
        if st.button("Encerrar Turno Agora", type="primary"):
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO Fechamentos (data_hora) VALUES (?)", (agora,))
            conn.commit()
            st.success("Caixa encerrado! Recarregue a página.")
    else:
        st.metric("💰 Faturamento Bruto (Entrou)", "R$ 0,00")
        st.metric("📈 Lucro Líquido Real (Sobrou)", "R$ 0,00")
        st.info("Aguardando as vendas de hoje...")
