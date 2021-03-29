import sys
import argparse
try:
    import simplejson as json
except ImportError:
    import json
from connectors.postgresql import PostgresqlConnector
from connectors.duckdb import DuckDBConnector
from flask import Flask,request,Response
app = Flask(__name__)

serverConfig = None
dbmsConfig = None
pools = {}
dbms = None

# handle SQL query requests for vega dataflow
@app.route("/query", methods = ["POST","GET"])
def executeQuery():
  client = None
  query = None
  try:
    if request.method == "POST":
      query = request.form["query"]
    else:
      query = request.args.get("query")
    if query is None:
      raise "request body must define query property"
    results = dbms.executeQuery(query)
    resp = Response(response=json.dumps(results),status=200, mimetype='application/json')
    h = resp.headers
    h['Access-Control-Allow-Origin'] = "*"
    return resp

  except Exception as err:
    #print(err)
    #return str(err)
    raise err

# handle requests to create and populate a table in the DBMS
@app.route("/createSql", methods = ["POST"])
def createSqlTable():
  client = None
  try:
    #params = request.get_json()
    #print(json.dumps(params))
    data = request.form["data"]
    name = request.form["name"]
    if not data:
      raise "request body must define data property";
    if not name:
      raise "request body must define name property";

    data = json.loads(data)
    schema = dbms.generateSchemaFromAllRecords(data)

    # Create table if it doesn't exist yet
    if dbms.checkTableExists(name):
      print("table %s already exists" % (name))
    else:
      print("table %s does not exist" % (name))
      print("creating table %s" % (name))
      print("built DBMS schema: %s" % (json.dumps(schema)))
      createTableQuery = dbms.generateCreateTableQuery(name, schema)
      print("running create query: '%s'" % (createTableQuery));
      dbms.executeQueryNoResults(createTableQuery)

      # Insert values
      # Build attribute list string e.g. (attr1, attr2, attr3)
      attrNames = schema.keys()

      insertStatements = []
      for row in data:
        st = "INSERT INTO " + name + " VALUES ( "
        for a in attrNames:
          out = row[a]
          if type(out) == str:
            out = row[a]
            out = out.replace("'", "''")
            out = out.replace("\"", "'" if serverConfig["keepquotes"] else "")
            if out[0] != "'" or out[-1] != "'": # no quotes
              out = "'" + out + "'"
          if out is None:
            out = "null"
          st += "{0},".format(out)
        st = st[:-1] + " );"
        insertStatements.append(st)
      print("running insert queries for %s" % (name))
      dbms.executeQueriesNoResults(insertStatements)
      print("insert queries complete")
    resp = Response(response="success",status=200)
    h = resp.headers
    h['Access-Control-Allow-Origin'] = "*"
    return resp

  except Exception as err:
    #print(err)
    #return str(err)
    raise err

def getConnector(dbmsName):
  if dbmsConfig["dbmsName"]  == "duckdb":
    return DuckDBConnector(dbmsConfig)
  elif dbmsConfig["dbmsName"]  == "postgresql":
    return PostgresqlConnector(dbmsConfig)
  else:
    raise Exception("dbms name not recognized: " + dbmsName)

if __name__ == "__main__":
    parser = argparse.ArgumentParser('Scalable Vega Version 1.0')
    parser.add_argument('--CI', action='store_true', default=False, help='Github Action CI Mode/Peer authentication instead of Trust')
    parser.add_argument('--db', type=str, default='postgresql', help='Database to be used')
    args = parser.parse_args()
    config_path = './config/'
    scf = config_path + "server.config.json"
    if args.db == 'postgresql':
      dcf = config_path + "postgresql.config.json"
    elif args.db == 'duckdb':
      dcf = config_path + "duckdb.config.json"
    else:
      raise Exception("DB not recognized/supported: " + args.db)

    with open(scf,"r") as f:
      serverConfig = json.load(f)
    with open(dcf,"r") as f:
      dbmsConfig = json.load(f)
    dbmsConfig['CI'] = args.CI
    dbms = getConnector(dbmsConfig["dbmsName"])
    app.run(debug=True,port=serverConfig["port"])
