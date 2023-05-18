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
from flask import Flask , request , jsonify

def bq(project_id, dataset_id, tables_id, credentials):
  client = bigquery.Client(credentials=credentials, project=project_id)
  sqlite_db_name = 'langchain_test.db'
  conn = sqlite3.connect(sqlite_db_name)

  for i in tables_id:

    sql = f'SELECT * FROM `{project_id}.{dataset_id}.{i}`'
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
  os.environ["OPENAI_API_KEY"] = os.environ["MY_SECRET_ENV"]
  llm = ChatOpenAI(model_name="gpt-3.5-turbo")
  project_id = request.args.get("project_id")
  dataset_id = request.args.get("dataset_id")
  tables_id = request.args.get("tables_id")
  credentials = request.args.get("credentials")
  query = request.args.get("query")

  dburi = bq(project_id, dataset_id, tables_id, credentials)
  db = SQLDatabase.from_uri(dburi)
  prompt = prompt()
  sql_query = db_chain(query,prompt)
  bq_query = chatgpt(sql_query)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)









