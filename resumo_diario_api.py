import streamlit as st
import pandas as pd
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
import csv, pytz

# Funções para obter os tickets do Freshdesk e gravar em um CSV
def get_not_closed_or_resolved_tickets():
    url = "https://azion.freshdesk.com/api/v2/tickets"
  #API KEY HEEEEEEEEEEREEEEEEEEEEEEEEEEE
    auth = HTTPBasicAuth("YOUR-API-KEY-HERE-VICTOR", "X")

    six_months_ago = datetime.now() - timedelta(days=6*30)
    six_months_ago_str = six_months_ago.strftime("%Y-%m-%d")
    params = {'updated_since': six_months_ago_str, 'per_page': 100}

    agent_mapping = {
        1063787817: 'Fernando vargas',
        1063206866: 'Lucas Aguiar',
        1065525755: 'Sergio Ferreira',
        1066023006: 'matheus chandelier',
        1062339453: 'Gregory Peres',
        1059647349: 'Eduardo Santos',
        1065525758: 'Alvin Michels',
        1059146958: 'Mateus Soares',
        1057249584: 'Eric Farias',
        1061673187: 'Lucas da Costa Furno'
    }

    not_closed_or_resolved_tickets = []

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
    with open('tickets.csv', 'w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(["Ticket ID", "Subject", "Type", "Agent", "Last update time"])
        
        for ticket in tickets:
            writer.writerow([ticket["id"], ticket["subject"], ticket["type"], ticket["responder_id"], ticket["updated_at"]])

# Gera o CSV
tickets = get_not_closed_or_resolved_tickets()
write_to_csv(tickets)

if tickets is not None:
    df = pd.read_csv('tickets.csv')
    df2 = df.copy()

    # Convert 'Last update time' to datetime
    df['Last update time'] = pd.to_datetime(df['Last update time']).dt.tz_convert('UTC')

    # Calculate the number of last update
    df['last update'] = (datetime.now(pytz.UTC) - df['Last update time']).dt.days




    # Check if update is needed (more than 2 days without update, or more than 4 days if includes a weekend)
    df['updt?'] = df.apply(lambda row: True if row['last update'] > 2 or 
                                  (row['last update'] > 4 and 
                                   ((row['Last update time'].weekday() < 5 and 
                                     row['Last update time'] + timedelta(days=row['last update']).weekday() >= 5) or
                                    row['Last update time'].weekday() >= 5)) else False, axis=1)

    #Change the data, adding patterns for slack use
    for index in df.index:
        df.loc[index, 'Ticket ID'] = "[" + str(int(df.loc[index, 'Ticket ID'])) + "]" + "(https://tickets.azion.com/a/tickets/" + str(int(df.loc[index, 'Ticket ID'])) +')'
        df.loc[index, 'tkt_id'] = str(int(df2.loc[index, 'Ticket ID']))
        df.loc[index, 'tkt_link'] = "https://tickets.azion.com/a/tickets/" + str(int(df2.loc[index, 'Ticket ID']))
        df['Agent'].mask(df['Agent'] == '@Fernando vargas', '@Fernando Amoretti', inplace=True)
        df.loc[index, 'Agent'] = "@" + str(df.loc[index, 'Agent'])



    #Ignore if there's no Agent    
    df = df[df['Agent'] != "@No Agent"]

    #DEFINE COLUMNS THAT WILL APPEAR
    df = df[['tkt_id', 'last update', "Agent", "Ticket ID", 'updt?']]

    #AG-GRID Lib configurations
    gb = GridOptionsBuilder.from_dataframe(df)
    groupDefaultExpanded= 1,
    gb.configure_default_column(editable=True)
    gb.configure_column('Ação tomada',
        cellEditor='agLargeTextCellEditor',
        lockPosition='right',
        cellEditorPopup=True  
    )

    #Define column pattern using de dataFrame information
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
    #Define column pattern using de dataFrame information
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
    #Define column pattern using de dataFrame information
    gb.configure_column(
        header_name= "Link",
        field= "Ticket ID",
        width=80,
        maxWidth=80,
        #rowGroup = True,
        sortable = True
    )
    #Grid Options
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
        

