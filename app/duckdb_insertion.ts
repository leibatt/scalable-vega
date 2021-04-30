var duckdb = require('duckdb');
var db = new duckdb.Database('./database/scalable-vega.db');
const format = require('pg-format');

global.fetch = require("node-fetch");

db.all('SELECT 42 AS fortytwo', function (err, res) {
	if (err) {
		throw err;
	}
	console.log(res[0].fortytwo);
});


function postgresTypeFor(value: any): string {
	// FixMe: want to use INTs too, if possible.
	// Client needs to send more type data in this case.
	const type = typeof value;
	if (type === 'string') {
		return 'VARCHAR(256)';
	} else if (type === 'number') {
		return 'FLOAT';
	} else if (type === 'boolean') {
		return 'BOOLEAN';
	} else {
		throw 'undefined type: \'' + type + '\'';
	}
}

function postgresSchemaFor(dataObj: any): string {
	const schema: any = {};
	for (var property in dataObj) {
		if (dataObj.hasOwnProperty(property)) {
			schema[property] = postgresTypeFor(dataObj[property]);
		}
	}
	return schema;
}

function createTableQueryStrFor(tableName: string, schema: any): string {
	let out: string = 'create table ' + tableName + '('
	let first: boolean = true;
	for (var attrName in schema) {
		if (!schema.hasOwnProperty(attrName)) {
			continue;
	}
		let attrType: string = schema[attrName];
		if (first) {
			first = false;
		} else {
			out += ', ';
		}
		out += (attrName + ' ' + attrType)
	}
	out += ');';
	return out;
}

function listToSQLTuple(l: any[], keepQuotes: boolean): string {
	let out: string = JSON.stringify(l);
	out = out.substring(1, out.length - 1);
	out = out.replace(/'/g, '\'\'');
	out = out.replace(/"/g, keepQuotes ? '\'' : '');
	return out;
}

var test_cases = ['cars', 'flights_20k', 'horizon_graph', 'normal_2d', 'pie_chart'];
var i;



for (i = 0; i < test_cases.length; i++) {
	var data_name = test_cases[i];
	var client = db.connect();
	const data = require('../data/' + data_name + '.json');
	const schema: any = postgresSchemaFor(data[0]);
	console.log('creating table ' + data_name);
	console.log('built postgres schema: ' + JSON.stringify(schema));
	const createTableQueryStr = createTableQueryStrFor(data_name, schema);
	console.log('running create query: ' + createTableQueryStr);
	client.run(createTableQueryStr);
	// Insert values
	// Build attribute list string e.g. (attr1, attr2, attr3)
	let attrNames: string[] = [];
	for (const attrName in schema) {
		if (!schema.hasOwnProperty(attrName)) {
			continue;
		}
		attrNames.push(attrName);
	}
	const attrNamesStr = listToSQLTuple(attrNames, false);
	// Transform data from JSON format into a 2d array where each row is a list of attribute values
	// with the same attribute order as the attribute list string above.
	const rows: any[] = [];
	for (let i: number = 0; i < data.length; i++) {
		const item: any = data[i];
		const row: any[] = [];
		for (let j: number = 0; j < attrNames.length; j++) {
			row.push(item[attrNames[j]]);
		}
		rows.push(row);
	}
	// Execute the insert queries.
	const queryStr = format('insert into ' + data_name + ' (' + attrNamesStr + ') values %L', rows);
	console.log('running insert queries for ' + data_name);
	client.run(queryStr);
	console.log('insert queries complete')
}






    
