import streamlit as st
import pandas as pd
from st_aggrid import GridOptionsBuilder, AgGrid
from st_aggrid import AgGrid, JsCode
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
import csv, pytz, base64
from io import StringIO

#Criado em Python 3.11
# Para rodar corretamente, instalar as libs com o comando "pip install streamlit pandas st-aggrid requests pytz"


# Configuração inicial da página, titulo icone e afins ( Precisa sempre estar aqui no topo )
st.set_page_config(
    page_title="Sup summary",
)
st.set_option('deprecation.showfileUploaderEncoding', False)

st.markdown("""
Get Tickets > fazer download > arrastar para a caixa
""")

# Uploader do CSV com os tickets
csv_data = st.file_uploader(label=':triangular_flag_on_post:  - :skull:  -  :knife:', type=['csv'])

# Cache para manter o arquivo salvo
# Necessário rodar o código do zero todo dia, evita pegar o mesmo CSV.
@st.cache
def get_not_closed_or_resolved_tickets():
    url = "https://azion.freshdesk.com/api/v2/tickets"
    auth = HTTPBasicAuth("SUA CHAVE DA API FRESHDESK AQUI", "X")

    six_months_ago = datetime.now() - timedelta(days=6*30)
    six_months_ago_str = six_months_ago.strftime("%Y-%m-%d")
    params = {'updated_since': six_months_ago_str, 'per_page': 100}

    #Dicionário com os IDS - Nomes dos técnicos - API do freshdesk entrega números.
    agent_mapping = {
        1063787817: 'Fernando vargas',
        1063206866: 'Lucas Aguiar',
        1065525755: 'Sergio Ferreira',
        1066023006: 'Chandelier',
        1062339453: 'Gregory Peres',
        1059647349: 'Eduardo Santos',
        1065525758: 'Alvin Michels',
        1059146958: 'Mateus Soares',
        1057249584: 'Eric Farias',
        1061673187: 'Lucas da Costa Furno',
        1061916486: 'Victor Rocha'
    }

    not_closed_or_resolved_tickets = []
#Conferir se API respondeu corretamente a request
    page = 1
    while True:
        params['page'] = page
        response = requests.get(url, auth=auth, params=params)

        if response.status_code != 200:
            raise Exception("Failed to get tickets: status code {}".format(response.status_code))

        tickets = response.json()
        if not tickets:
            break

        for ticket in tickets:
            if ticket['status'] not in [5, 4]:
                ticket['responder_id'] = agent_mapping.get(ticket['responder_id'], "Unknown agent")
                not_closed_or_resolved_tickets.append(ticket)
        
        page += 1

    return not_closed_or_resolved_tickets

def write_to_csv(tickets):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ticket ID", "Subject", "Type", "Agent", "Last update time"])
    
    for ticket in tickets:
        writer.writerow([ticket["id"], ticket["subject"], ticket["type"], ticket["responder_id"], ticket["updated_at"]])
    
    # Converte e poe em base 64
    output_str = output.getvalue()
    b64 = base64.b64encode(output_str.encode('utf-8-sig')).decode()

    # Use the markdown component of Streamlit to display the download link
    href = f'<a href="data:file/csv;base64,{b64}" download="tickets.csv">Download Tickets CSV File</a>'
    st.markdown(href, unsafe_allow_html=True)

# Cria um botão no Streamlit para obter os tickets
if st.button('Get Tickets'):
    tickets = get_not_closed_or_resolved_tickets()
    write_to_csv(tickets)

# Carregar o DataFrame no estado da sessão se ele ainda não estiver carregado
if csv_data is not None and 'df' not in st.session_state:
 # Carrega o CSV gerado para um DataFrame
    df = pd.read_csv(csv_data)
    df2 = df.copy()

    # Converte 'Last update time' para datetime
    df['Last update time'] = pd.to_datetime(df['Last update time']).dt.tz_convert('UTC')

    # Calcula o last update(dias)
    df['last update'] = (datetime.now(pytz.UTC) - df['Last update time']).dt.days

    # Checa se há necessidade de atualização (mais de 2 dias sem atualização, ou mais de 4 dias se incluir um fim de semana).
    df['updt?'] = df.apply(lambda row: True if row['last update'] > 2 or 
                                (row['last update'] > 4 and 
                                ((row['Last update time'].weekday() < 5 and 
                                    row['Last update time'] + timedelta(days=row['last update']).weekday() >= 5) or
                                    row['Last update time'].weekday() >= 5)) else False, axis=1)

    #Altere a estrutura para Markdown para formatação no Slack
    for index in df.index:
        df.loc[index, 'Ticket ID'] = "[" + str(int(df.loc[index, 'Ticket ID'])) + "]" + "(https://tickets.azion.com/a/tickets/" + str(int(df.loc[index, 'Ticket ID'])) +')'
        df.loc[index, 'tkt_id'] = str(int(df2.loc[index, 'Ticket ID']))
        df.loc[index, 'tkt_link'] = "https://tickets.azion.com/a/tickets/" + str(int(df2.loc[index, 'Ticket ID']))
        df['Agent'].mask(df['Agent'] == '@Fernando vargas', '@Fernando Amoretti', inplace=True)
        df.loc[index, 'Agent'] = "@" + str(df.loc[index, 'Agent'])



    #Ignore se não tiver agente   
    df = df[df['Agent'] != "@No Agent"]

    #Definir colunas que são mostradas
    df = df[['tkt_id', 'last update', "Agent", "Ticket ID", 'updt?']]
    st.session_state.df = df

# Se o DataFrame já estiver carregado no estado da sessão, basta usá-lo
if 'df' in st.session_state:
    df = st.session_state.df

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_grid_options(enableCellChangeFlash=False, suppressFlashOnNewData=True)
    
    # AG-GRID Configuração de cada uma das colunas
    # gb = GridOptionsBuilder.from_dataframe(df)
    groupDefaultExpanded= 1,
    gb.configure_default_column(editable=True)
    gb.configure_column('Ação tomada',
        cellEditor='agLargeTextCellEditor',
        lockPosition='right',
        cellEditorPopup=True  
    )

    gb.configure_column(
        header_name="Link", 
        field = "tkt_id",
        resizable = False,
        sortable = True,
        lockPosition='left',
        width=100,
        maxWidth = 82,
        cellRenderer=JsCode('''function(params)  {
    if (params.value != undefined)
    {return '<a href="https://tickets.azion.com/a/tickets/' + params.value + '" target="_blank">'+params.value+'</a>'}}''')
        )

    gb.configure_column(
        header_name= "Agent",
        field= "Agent",
        width=114,
        maxWidth = 150,
        columnGroupShow= 'open',
        rowGroup = True,
        hide = True,
        groupDefaultExpanded= -1,
        sortable = True
    )

    gb.configure_column(
        header_name="updt?",
        field="updt?",
        hide=True,
    )

    gb.configure_column(
    header_name="last update",
    field="last update",
    cellStyle=JsCode('''function(params)  {
        if (params.value >= 2) {
            return {backgroundColor: 'red'}
        } else {
            return {}
        }
    }''')
    )

    gb.configure_column(
        header_name="L.Upd",
        field="last update",
        width=25,
        maxWidth = 150
    )

    gb.configure_column(
        header_name= "Link",
        field= "Ticket ID",
        width=80,
        maxWidth=80,
        #rowGroup = True,
        sortable = True
    )
    # Configurações do Grid
    gb.configure_grid_options(enableRangeSelection=True, groupDefaultExpanded = -1,)
    gb.configure_selection('multiple', use_checkbox=True, groupSelectsFiltered=True) 
    response = AgGrid(
            df,
            gridOptions=gb.build(),
            fit_columns_on_grid_load=True,
            allow_unsafe_jscode=True,
            groupDefaultExpanded= -1,
            enable_enterprise_modules=True,  
        )


    # Salvar as alterações feitas no DataFrame de volta no estado da sessão
    if response['data'] is not None:
        st.session_state.df = response['data']
