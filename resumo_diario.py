import streamlit as st
import pandas as pd
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
#Initial page configurations
st.set_page_config(
    #layout="wide",
    page_title="Support summary",
    )
st.set_option('deprecation.showfileUploaderEncoding', False)

#Open the file
st.write(":triangular_flag_on_post:  - :skull:")
csv_data = st.file_uploader(label='Importe o CSV do resumo', type=['csv'])

if csv_data is not None:
    df = pd.read_csv(csv_data)
    df2 = df.copy()
    
    #Change the data, adding patterns for slack use
    for index in df.index:
        df.loc[index, 'Ticket ID'] = "[" + str(df.loc[index, 'Ticket ID']) + "]" + "(https://tickets.azion.com/a/tickets/" + str(df.loc[index, 'Ticket ID']) +')'
        df.loc[index, 'tkt_id'] = df2.loc[index, 'Ticket ID']
        df.loc[index, 'tkt_link'] = "https://tickets.azion.com/a/tickets/" + str(df2.loc[index, 'Ticket ID'])
        df['Agent'].mask(df['Agent'] == '@Fernando vargas', '@Fernando Amoretti', inplace=True)
        df.loc[index, 'Agent'] = "@" + df.loc[index, 'Agent']
    #Ignore if theres no Agent    
    df = df[df['Agent'] != "@No Agent"]

    #DEFINE COLIMNS THAT WILL APPEAR
    df =df[['tkt_id', "Agent", "Ticket ID", ]]
    

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
        
