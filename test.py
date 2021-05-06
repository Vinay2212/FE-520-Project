# import yfinance as yf
#
# a = 'APPL'
#
# msft = yf.Ticker(a)
# data = msft.history(period="max")
# print(data)
#
# company_name = msft.info['longName']
# print(company_name)
# #Output = 'Microsoft Corporation'

import plotly.express as px

df = px.data.stocks()
fig = px.line(df, x='date', y="AAPL")
fig.show()