from dash import Dash, dcc, html, dash_table, Input, Output, State, callback
import dash

import base64
import datetime
import io

import pandas as pd
import dash_bootstrap_components as dbc


#### jinja2 stuff
##from jinja2 import Environment, PackageLoader, select_autoescape
##env = Environment(
##    loader=PackageLoader("kedro_graphql.ui"),
##    autoescape=select_autoescape()
##)
##
##external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
##
##app = Dash(__name__, external_stylesheets=external_stylesheets)
##
##app.layout = html.Div([
##    html.Div([dash.__version__]),
##    dcc.Upload(
##        id='upload-data',
##        children=html.Div([
##            'Drag and Drop or ',
##            html.A('Select Files')
##        ]),
##        style={
##            'width': '100%',
##            'height': '60px',
##            'lineHeight': '60px',
##            'borderWidth': '1px',
##            'borderStyle': 'dashed',
##            'borderRadius': '5px',
##            'textAlign': 'center',
##            'margin': '10px'
##        },
##        # Allow multiple files to be uploaded
##        multiple=True
##    ),
##    html.Div(id='output-data-upload'),
##])
##
##def create_datacatalog(list_of_contents, list_of_names, list_of_dates):
##    try:
##        timestamp = datetime.datetime.now()
##        parameters = {"datasets": list_of_names,
##                      "year": timestamp.year,
##                      "month": timestamp.month,
##                      "day": timestamp.day,
##                      "timestamp": timestamp.isoformat()}
##        template = env.get_template("template.yaml")
##        catalog = template.render(parameters)
##    except Exception as e:
##        print(e)
##        return html.Div([
##            'There was an error processing this file.'
##        ])
##
##    return html.Div([
##        html.H5("Data Catalog"),
##
##
##        html.Hr(),  # horizontal line
##
##        # For debugging, display the raw contents provided by the web browser
##        html.Pre(catalog)
##    ])
##
##def parse_contents(contents, filename, date):
##    content_type, content_string = contents.split(',')
##
##    decoded = base64.b64decode(content_string)
##    try:
##        if 'csv' in filename:
##            # Assume that the user uploaded a CSV file
##            df = pd.read_csv(
##                io.StringIO(decoded.decode('utf-8')))
##        elif 'xls' in filename:
##            # Assume that the user uploaded an excel file
##            df = pd.read_excel(io.BytesIO(decoded))
##    except Exception as e:
##        print(e)
##        return html.Div([
##            'There was an error processing this file.'
##        ])
##
##    return html.Div([
##        html.H5(filename),
##        html.H6(datetime.datetime.fromtimestamp(date)),
##
##        dash_table.DataTable(
##            df.to_dict('records'),
##            [{'name': i, 'id': i} for i in df.columns]
##        ),
##
##        html.Hr(),  # horizontal line
##
##        # For debugging, display the raw contents provided by the web browser
##        html.Div('Raw Content'),
##        html.Pre(contents[0:200] + '...', style={
##            'whiteSpace': 'pre-wrap',
##            'wordBreak': 'break-all'
##        })
##    ])
##
##@callback(Output('output-data-upload', 'children'),
##              Input('upload-data', 'contents'),
##              State('upload-data', 'filename'),
##              State('upload-data', 'last_modified'))
##def update_output(list_of_contents, list_of_names, list_of_dates):
##    if list_of_contents is not None:
##        children = [
##            create_datacatalog(list_of_contents, list_of_names, list_of_dates)]
##        return children


app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "backgroundColor": "#f8f9fa",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

app.layout =  html.Div(
    [
        html.H2("Sidebar", className="display-4"),
        html.Hr(),
        html.P(
            "A simple sidebar layout with navigation links", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/", active="exact"),
                dbc.NavLink("Page 1", href="/page-1", active="exact"),
                dbc.NavLink("Page 2", href="/page-2", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)


if __name__ == '__main__':
    app.run(debug=True)