import dash #DASHBOARD
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

import dash_table
from datetime import datetime as dt
from datetime import date, timedelta
import pandas as pd

import folium #MAP
from folium import plugins
from folium.plugins import HeatMap
from folium.plugins import MarkerCluster

import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

import pandas as pd
import numpy as np

#PYTHON
from enlaceInfo import RiskScore
from sklearn.linear_model import  LassoLarsIC


#INICIALIZE
print(dcc.__version__) # 0.6.0 or above is required
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

#app.config.suppress_callback_exceptions = True


# ============================ METHODS ============================
# Por default: General
df = pd.read_csv('data/example_criteria_2.csv')
edo = pd.read_csv("data/estados.csv", encoding = 'latin-1')
# ============================ ELEMENTS ============================
estado_dropdown = dbc.FormGroup(
    [
        dbc.Label("Selecciona un estado"),
        dcc.Dropdown(
            id="estado_dropdown",
            #options=edo.to_dict("records"),
            value=0,
        ),
    ]
)

estado_checklist = dbc.FormGroup(
    [
        #dbc.Label("Extras:"),
        dbc.Checklist(
            id="estado_checklist",
            #options=edo[1:].to_dict("records"),
            value=[],
            inline=True,
        ),
    ]
)

button = html.Div(
    [
        dbc.Button("Enviar", id="button_envia", outline=True, color="primary", className="mr-1"),
        html.Span(id="button_2", style={"vertical-align": "middle"}),
    ]
)

fade = html.Div(
    [
        dbc.Button("Agregar más estados", id="fade-button", className="mb-3"),
        dbc.Fade(
            dbc.Card(
                dbc.CardBody(
                    estado_checklist
                    #html.P(
                    #    "This content fades in and out", className="card-text"
                    #)
                )
            ),
            id="fade",
            is_in=False,
            appear=False,
        ),
    ]
)



tipoEscuela = dbc.FormGroup(
    [
        dbc.Label("Tipo de escuela:"),
        dbc.RadioItems(
            id="tipoEscuela",
            options=[
                {"label": "General", "value": "G"},
                {"label": "Indigena", "value": "I"},
                {"label": "Comunitaria", "value": "C"},
                {"label": "General -Publica", "value": "Pub"},
                {"label": "General -Privada", "value": "Pri"},
            ],
            value="G",
            inline=True,
        ),
    ]
)

table =  html.Div([
        dash_table.DataTable(
            style_data={'whiteSpace': 'normal'},
            css=[{
                'selector': '.dash-cell div.dash-cell-value',
                'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
            }],
            id='criteria_table',
            columns=[{"name": i, "id": i, } for i in df.columns],
            data = df.to_dict('records'),
            fixed_rows={ 'headers': True, 'data': 0 },
            #style_cell={'width': '100px'},
            style_cell_conditional=[
                {'if': {'column_id': 'Variable'},
                'width': '20%'},
                {'if': {'column_id': 'Puntos'},
                'width': '15%'},
                {'if': {'column_id': 'Condicion'},
                'width': '30%'},
            ],
            style_table={
            'height': '300px',
            'width': "500px",
            #'overflowY': 'scroll',
            'border': 'thin lightgrey solid'
            },
           )
    ], style={'width': '49%', 'display': 'inline-block'}),
       
alerta = dbc.Alert(
            "Hello! I am an alert that doesn't fade in or out",
            id="alert-no-fade",
            dismissable=True,
            fade=False,
            is_open=True,
        ),

mensaje = html.Div([
    dcc.Input(id='my-id', value='initial value', type='text'),
    html.Div(id='my-div')
]),
######################## START RESULTS ########################
layout_results =  html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                   # html.Div(id='my-div'),
                    html.Div([
                        html.H1("Esto es una prueba"),
                    ]) ,width="auto", align="center"
                ),
            ], justify="center",
        ),
        dbc.Row([
            dbc.Col([
                estado_dropdown,
                html.Div(html.P(id="radioitems-checklist-output")),
            ], width={"size":4, "offset":1}, align="center"),
            dbc.Col(tipoEscuela, width={"size":6}, align="center"),
            ]
        ),
        dbc.Row(
            #html.Div(html.P(id="radioitems-checklist-output")),
            dbc.Col(fade, width={"size":10, "offset":1}, align="center"),
            #dbc.Col(submit, align="center",width={"size":2}),
            ),
        dbc.Row(
            dbc.Col(button, align="center",width={"size":2, "offset":5}),
        ),

        dbc.Row(
            [
                dbc.Col(
                    html.Div([
                        html.Iframe(id = "map", srcDoc = open("mapas/mapa_base.html", 'r').read(), width=500, height=300),
                        ]), width={"size":4, "offset":1},align="center"
                ),
                dbc.Col(table, width={"size":6,"offset":1 }, align="center"),
            ]
        )
    ]
)


app.layout = layout_results

@app.callback(
    Output("fade", "is_in"),
    [Input("fade-button", "n_clicks")],
    [State("fade", "is_in")],
)
def toggle_fade(n, is_in):
    if not n:
        # Button has never been clicked
        return False
    return not is_in

#Update table and map
#and later download csv
@app.callback(
    [Output('criteria_table', "data"),
    Output("map", "srcDoc")],
    [Input('button_envia', "n_clicks")],
    [State('tipoEscuela', "value"),
     State("estado_checklist", "value"),
     State("estado_dropdown", "value")])
def update_table(n_clicks, value_tipo, value_estados, value_estado):
    #return n_clicks
    if n_clicks is None:
        raise PreventUpdate
    else: 
        if len(value_estados) == 0 and value_estado == None:
            raise PreventUpdate

        lista_estados = value_estados
        if value_estado != None:
            estado = int(value_estado)
        #Caso 1: Solo estado 
        if len(lista_estados) == 0 and value_estado != None:
            estado = int(value_estado)
            lista_final = [estado]
        #Caso 2: Solo en lista
        if len(lista_estados) > 0 and value_estado == None:
            lista_estados = list(map(int, lista_estados))
            lista_final = lista_estados
        #Caso 3: En ambos
        if len(lista_estados) > 0 and value_estado != None:
            estado = int(value_estado)
            lista_final = [estado]
            lista_estados = list(map(int, lista_estados))
            lista_final = lista_final + lista_estados #Nacional va primero
        tipo = value_tipo
        reg = LassoLarsIC(criterion='aic')
        info_rs = RiskScore()
        dicc_results = info_rs.get_all_info_filtered(lista_final,tipo, reg)
        criteria = dicc_results["criteria"].to_dict('records')
     
        id_map = int(''.join(map(str,lista_final)))
        nombre = "mapas/mapa_"+ tipo + "_" + str(id_map) + ".html"
        info_rs.get_map(dicc_results["risk"], nombre)
        return criteria, open(nombre, 'r').read()

@app.callback(
    Output("radioitems-checklist-output", "children"),
    [
        Input("estado_checklist", "value"),
        Input("estado_dropdown", "value"),
    ],
)
def on_form_change(checklist_value, n_drop):
    error = "Por favor selecciona un estado."

    n_checkboxes = len(checklist_value)

    if n_drop == None and n_checkboxes ==0:
        output_string = error
    else:
        output_string = ""

    return output_string


##Update Dropdown
@app.callback(
    [Output('estado_dropdown', 'options'),
    Output('estado_checklist', 'options')],
    [Input('tipoEscuela', 'value')]
)
def update_date_dropdown(tipo):
    if tipo == "I":
        edo = pd.read_csv("data/estados_ind.csv", encoding = 'latin-1')
    else:
        edo = pd.read_csv("data/estados.csv", encoding = 'latin-1')
    return edo.to_dict("records"), edo[1:].to_dict("records")


################################# MAIN ################################
if __name__ == '__main__':
    app.run_server(debug=True)