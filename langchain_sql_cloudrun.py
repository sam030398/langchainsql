# -*- coding: utf-8 -*-
"""Langchain SQL-CLoudRun.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1g_31lNGq3SlhkfHBi9I-atOl86dZAGrU
"""


import os
import sqlite3
from google.cloud import bigquery
from google.oauth2 import service_account
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.agents import AgentExecutor
from langchain.chat_models import ChatOpenAI
from langchain import OpenAI, SQLDatabase, SQLDatabaseChain
from langchain.prompts.prompt import PromptTemplate
from google.cloud import secretmanager

from flask import Flask , request , jsonify
def access_secret_version(name):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')

def bq(project_id, dataset_id, tables_id, credentials):
  client = bigquery.Client(credentials=credentials, project=project_id)
  sqlite_db_name = 'langchain_test.db'
  conn = sqlite3.connect(sqlite_db_name)
  sql = f'SELECT * FROM `{project_id}.{dataset_id}.{tables_id}`'
  query_job = client.query(sql)
  results = query_job.result().to_dataframe()
  sqlite_table_name = i
  results.to_sql(sqlite_table_name, conn, if_exists='replace', index=False)

  conn.commit()
  conn.close()
  sqlite_connection_string = f'sqlite:///{os.path.abspath(sqlite_db_name)}'
  print(f'SQLite connection string: {sqlite_connection_string}')
  return sqlite_connection_string

def prompt():

  _DEFAULT_TEMPLATE2 = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.
  Use the following format:

  Question: "Question here"
  SQLQuery: "SQL Query to run"
  SQLResult: "Result of the SQLQuery"
  Answer: "Final answer here"

  Only use the following tables:

  {table_info}

  If user asks for CARS table, they want a customer analytics table. 
  1. First, you need to join both customers and order tables together using the customer id column as join key.
  2. Then you need to derive sales metrics and consolidate the results into a singular table.



  Else:
  1. By mainly using CARS table, try to come up with a query to answer the given question. 
  2. Always use customer__id column as an unique indefier for each customer. 
  3. Always use id column as an unique indefier for each order. 


  Limit the output to only 1 row

  Question: {input}"""


  PROMPT2 = PromptTemplate(
      input_variables=["input", "table_info", "dialect"], template=_DEFAULT_TEMPLATE2
  )

  return PROMPT2


def db_chain(query,prompt):
  db_chain = SQLDatabaseChain.from_llm(llm, db, prompt=prompt, verbose=True, return_intermediate_steps=True, top_k=1)
  results = db_chain(query)
  sql_query = results["intermediate_steps"][0]
  return sql_query

def chatgpt(query):
  import openai
  sql_query = db_chain(query)
  project_id = 'pt-client-project'
  dataset_id = 'Club21'
  query = f"""Convert this SQL Query below to be executed in Bigquery. Just print out the query. The project_id would be {project_id} and dataset would be {dataset_id}.
  {query}
  """
  completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo", # this is "ChatGPT" $0.002 per 1k tokens
    messages=[{"role": "user", "content": query}]
  )
  bq_query = completion.choices[0].message.content
  return bq_query

from flask import Flask
app = Flask(__name__)

@app.route("/",methods=["GET"])
def main():
  os.environ["OPENAI_API_KEY"] = access_secret_version("projects/354659879420/secrets/openai/versions/1")
  llm = ChatOpenAI(model_name="gpt-3.5-turbo")
  #project_id = request.args.get("project_id")
  project_id = 'pt-client-project'
  #dataset_id = request.args.get("dataset_id")
  dataset_id = 'Club21'
  #tables_id = request.args.get("tables_id")
  tables_id = 'Orders'
  #credentials = request.args.get("credentials")
  credentials = """
    {
  "type": "service_account",
  "project_id": "pt-client-project",
  "private_key_id": "f16c69af6d4a76475ddeec84220e8de2f4e5b472",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCiMTDQdxCgWNuB\nwV3ZDqWGX6ERd9a7dSgwi0YhrEahnHTYR3TbZrlm/Eqa/0bayqT+JILcP1wdCF0W\nF2+cTG+mymAnM0OjhUxifK5pCl9SGw8Gy8TKg2eZav9P3xE59+8TKaHZYXpb3xII\nwPKlxXzM8KYCwEj7EBpsNJer178HBKtgxs6zO+8xxV/5Ge2RQtJqbSDHxCidcO5Y\nv+dKOx8fQfHAsJVs+7HWW1LraS50hrL2ur5kl26F0zN8x+Hqkzd0hNqN52s5KGXp\nyYZfPfpBAFKO606NPnqRezq8IhUfsv768QMhVci5TsZVdIHaAFjjmHiYtqWO1igf\nH2KIxCYHAgMBAAECggEANWpM4MLtq1lIRXX44eTUd6oj4hxdEFSXvVEI8ksJ4eyk\ngJwb7KvqkHOzYFOFMsY9S2Ob40xMmlUoTv+95rQ3qy8INrDH7GEYlHDqgbaESQaX\nTs4qC+X15w1ZcyUMR9KTHnT+FBjp0rrm9hIRd63QGbCBg/NutZyKjytM7i+5/mWx\nj07t+CvyaOlAEcXCHNTK8G51Xy7grLuatTlWpipLSVmx4Oa7f5sqAeqWW1F3Mr2T\n6ibYEwD+8L7YtjBbaeEuspKcc6paHEuytxnBP2hj5grFAJlvGqay7JIWS4//Xc9s\nKt7spuHmNKxAadzyw+W9c2Ctrs1eYuPWwwEG9qgoKQKBgQDOOo2ZbgLXFQDNKWml\n+9S9V3kZWQ6704zJD7iz5B8goZYwRyO9aOshgOcTlnQI+vn5t0HuY93M9AO3suwF\nz+xWF5cKQ0CvHiMZIU3spOHXDqBrnYDS/fxNa7kX0AfixBxfuniJEY3Fanai8QOK\niBx0hA+F2CZe/FNtb2vMSoZ8bwKBgQDJVewY1SmAhpI8aodnAJCYKH5uMBL9z4oj\nyvbATnQUagF4y8HAJ1TJUxSuR6toKpCKftRw+ZoQYJWUPst0de0nwqsPZPF/LJ5e\n7UIHiMwl95P9IWNen7fFPiHkIn+6Gi2NbWYOeT3za2BP9twlTPAuib8UqzCJv9uy\nNqzeOY3r6QKBgHtVdT2fFz++Jd6Mt8w2kYIzAA9yvWcDG51bM6ER+rOvL3zr7qnm\nR0igKJIEVpzQTBNVz65cN1fNTzPbY2AOe075iLDwi4yvP1pWGp499XqCGtqBNXv5\nvZwnomhlV3H8yuNNR6zhvKGmDBFihjWhNTNRj18CZ+BCkzpNenCQ2WEtAoGAHKD6\nJIHTF/KKwsqHHG9pICnJ6JMvcCXdx78pnSjKushkEzAuCcvN8567txh72CENUpQ8\nUyA69w801dKkDZhjM58rwdGhwWqvzmHAXN/n35I32euwfJkLgaGXIiCBtw3X4l9m\n/rHgzEc9d8FrhmZNVODDagX5rey5Kbs6k5LtilkCgYEAgmT1PqxR2zYnk3hgMkW3\n3HYCE3hCLRraTrWeQTVkLLp8kR0LYm+YifzDTD3JxGJXvwANP8QNpfhnZXa0swpJ\nxkcgoUnWR/g/mlFDB0pSMXRQjXU7o7Y4A9cN43JewGnxD+4QCZulvkGojChWD95O\nUnD1LliHMIvhT6GvzJlg/Dw=\n-----END PRIVATE KEY-----\n",
  "client_email": "704947980487-compute@developer.gserviceaccount.com",
  "client_id": "108800423936007394236",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/704947980487-compute%40developer.gserviceaccount.com"
}      """
  #query = request.args.get("query")
  query = "Who are the top 10 spending customers?"
  dburi = bq(project_id, dataset_id, tables_id, credentials)
  db = SQLDatabase.from_uri(dburi)
  prompt = prompt()
  sql_query = db_chain(query,prompt)
  bq_query = chatgpt(sql_query)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)









